"""Extract forms from frontend code."""

import logging
import re
from pathlib import Path

from config.settings import Language
from core.types import FormField, FormInfo
from core.utils import generate_id
from indexers.unified_indexer import UnifiedIndexer

logger = logging.getLogger(__name__)


class FormExtractor:
    """Extract forms from frontend code."""

    def __init__(self, project_root: Path):
        self.root = project_root

    async def extract_all(self, indexer: UnifiedIndexer) -> list[FormInfo]:
        """Extract all forms from indexed files."""
        forms = []

        for file_info in indexer.file_index.all_files():
            if file_info.language not in (
                Language.TYPESCRIPT,
                Language.TSX,
                Language.JAVASCRIPT,
                Language.JSX,
            ):
                continue

            content = indexer.get_file_content(file_info.path)
            if not content:
                continue

            # React Hook Form
            if "useForm" in content:
                forms.extend(self._extract_rhf(content, file_info.path))

            # Formik
            if "useFormik" in content or "<Formik" in content:
                forms.extend(self._extract_formik(content, file_info.path))

            # HTML forms
            for m in re.finditer(r"<form[^>]*>(.*?)</form>", content, re.DOTALL | re.I):
                form = self._extract_html_form(m.group(1), file_info.path, content)
                if form:
                    forms.append(form)

        logger.info(f"Extracted {len(forms)} forms")
        return forms

    def _extract_rhf(self, content: str, file: str) -> list[FormInfo]:
        """Extract React Hook Form forms."""
        forms = []
        comp = re.search(r"(?:function|const)\s+(\w+)", content)
        component = comp.group(1) if comp else None

        fields = []
        validation_schema = None

        # Default values
        defaults = re.search(r"defaultValues\s*:\s*(\{[^}]+\})", content)
        if defaults:
            for m in re.finditer(r"(\w+)\s*:", defaults.group(1)):
                fields.append(
                    FormField(name=m.group(1), field_type=self._infer_type(m.group(1)))
                )

        # Register calls
        for m in re.finditer(
            r'register\s*\(\s*[\'"](\w+)[\'"](?:\s*,\s*(\{[^}]*\}))?', content
        ):
            name = m.group(1)
            opts = m.group(2) or ""

            if not any(f.name == name for f in fields):
                fields.append(
                    FormField(
                        name=name,
                        field_type=self._infer_type(name),
                        required="required" in opts.lower(),
                        min_length=self._extract_int(opts, r"minLength\s*:\s*(\d+)"),
                        max_length=self._extract_int(opts, r"maxLength\s*:\s*(\d+)"),
                        pattern=self._extract_pattern(opts),
                    )
                )

        if "zodResolver" in content:
            validation_schema = "zod"
        elif "yupResolver" in content:
            validation_schema = "yup"

        if fields:
            forms.append(
                FormInfo(
                    id=generate_id(),
                    file=file,
                    component=component,
                    fields=fields,
                    submit_endpoint=self._find_submit(content),
                    validation_lib=f"react-hook-form{'+' + validation_schema if validation_schema else ''}",
                )
            )

        return forms

    def _extract_formik(self, content: str, file: str) -> list[FormInfo]:
        """Extract Formik forms."""
        forms = []
        comp = re.search(r"(?:function|const)\s+(\w+)", content)
        component = comp.group(1) if comp else None

        fields = []

        # Initial values
        init = re.search(r"initialValues\s*[:=]\s*(\{[^}]+\})", content)
        if init:
            for m in re.finditer(r"(\w+)\s*:", init.group(1)):
                fields.append(
                    FormField(name=m.group(1), field_type=self._infer_type(m.group(1)))
                )

        # Field components
        for m in re.finditer(r'<Field[^>]*name\s*=\s*[\'"](\w+)[\'"][^>]*>', content):
            name = m.group(1)
            if not any(f.name == name for f in fields):
                fields.append(FormField(name=name, field_type=self._infer_type(name)))

        if fields:
            forms.append(
                FormInfo(
                    id=generate_id(),
                    file=file,
                    component=component,
                    fields=fields,
                    submit_endpoint=self._find_submit(content),
                    validation_lib="formik",
                )
            )

        return forms

    def _extract_html_form(
        self, form_content: str, file: str, full_content: str
    ) -> FormInfo | None:
        """Extract HTML form."""
        fields = []

        for m in re.finditer(
            r'<input[^>]*name\s*=\s*[\'"](\w+)[\'"][^>]*>', form_content, re.I
        ):
            name = m.group(1)
            tag = m.group(0)
            type_m = re.search(r'type\s*=\s*[\'"](\w+)[\'"]', tag)
            fields.append(
                FormField(
                    name=name,
                    field_type=type_m.group(1) if type_m else "text",
                    required="required" in tag.lower(),
                )
            )

        for m in re.finditer(
            r'<textarea[^>]*name\s*=\s*[\'"](\w+)[\'"]', form_content, re.I
        ):
            fields.append(FormField(name=m.group(1), field_type="textarea"))

        for m in re.finditer(
            r'<select[^>]*name\s*=\s*[\'"](\w+)[\'"]', form_content, re.I
        ):
            fields.append(FormField(name=m.group(1), field_type="select"))

        if not fields:
            return None

        comp = re.search(r"(?:function|const)\s+(\w+)", full_content)
        return FormInfo(
            id=generate_id(),
            file=file,
            component=comp.group(1) if comp else None,
            fields=fields,
            submit_endpoint=self._find_submit(full_content),
        )

    def _infer_type(self, name: str) -> str:
        """Infer input type from field name."""
        hints = {
            "email": "email",
            "password": "password",
            "phone": "tel",
            "tel": "tel",
            "date": "date",
            "age": "number",
            "price": "number",
            "amount": "number",
            "quantity": "number",
            "url": "url",
        }
        name_lower = name.lower()
        for hint, typ in hints.items():
            if hint in name_lower:
                return typ
        return "text"

    def _find_submit(self, content: str) -> str | None:
        """Find form submit endpoint."""
        patterns = [
            r'onSubmit[^{]*\{[^}]*(?:fetch|axios)[^\'"`]*[\'"`]([^\'"`]+)[\'"`]',
            r'handleSubmit[^{]*\{[^}]*(?:fetch|axios)[^\'"`]*[\'"`]([^\'"`]+)[\'"`]',
            r"action\s*=\s*['\"]([^'\"/][^'\"]*\/[^'\"]*)['\"]",
        ]
        for p in patterns:
            m = re.search(p, content, re.DOTALL)
            if m:
                ep = m.group(1)
                if "/api/" in ep or ep.startswith("/"):
                    return ep
        return None

    def _extract_int(self, text: str, pattern: str) -> int | None:
        """Extract integer from pattern."""
        m = re.search(pattern, text)
        return int(m.group(1)) if m else None

    def _extract_pattern(self, opts: str) -> str | None:
        """Extract regex pattern from options."""
        m = re.search(r"pattern\s*:\s*/([^/]+)/", opts)
        return m.group(1) if m else None
