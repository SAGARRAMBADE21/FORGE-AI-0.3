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

            # Check most specific form libraries first to avoid duplicates
            
            # TanStack Form (check first - most specific with package name)
            if "useForm" in content and "@tanstack/react-form" in content:
                forms.extend(self._extract_tanstack_form(content, file_info.path))
            # Shadcn/Radix Form (uses react-hook-form under the hood, check before generic RHF)
            elif "<Form" in content and "FormField" in content:
                forms.extend(self._extract_shadcn_form(content, file_info.path))
            # Formik
            elif "useFormik" in content or "<Formik" in content:
                forms.extend(self._extract_formik(content, file_info.path))
            # React Hook Form (generic, check last)
            elif "useForm" in content:
                forms.extend(self._extract_rhf(content, file_info.path))

            # Next.js Server Actions
            if "use server" in content or "formAction" in content:
                forms.extend(self._extract_server_action_form(content, file_info.path))

            # HTML forms
            for m in re.finditer(r"<form[^>]*>(.*?)</form>", content, re.DOTALL | re.I):
                form = self._extract_html_form(m.group(1), file_info.path, content)
                if form:
                    forms.append(form)

        logger.info(f"Extracted {len(forms)} forms")
        return forms

    def _extract_shadcn_form(self, content: str, file: str) -> list[FormInfo]:
        """Extract Shadcn/Radix UI forms."""
        forms = []
        comp = re.search(r"(?:function|const)\s+(\w+)", content)
        component = comp.group(1) if comp else None

        fields = []
        validation_lib = "react-hook-form+shadcn"

        # Extract from FormField name attributes
        for m in re.finditer(r'<FormField[^>]*name\s*=\s*[\'"](\w+)[\'"]', content):
            name = m.group(1)
            if not any(f.name == name for f in fields):
                fields.append(FormField(
                    name=name,
                    field_type=self._infer_type(name),
                ))

        # Check for Zod resolver
        if "zodResolver" in content:
            validation_lib += "+zod"
            # Try to find connected Zod schema
            zod_match = re.search(r'zodResolver\s*\(\s*(\w+)Schema\s*\)', content)
            if zod_match:
                schema_name = zod_match.group(1)
                # Extract fields from Zod schema if defined in same file
                schema_match = re.search(
                    rf'const\s+{schema_name}Schema\s*=\s*z\.object\(\s*\{{([^}}]+)\}}',
                    content, re.DOTALL
                )
                if schema_match:
                    zod_fields = self._parse_zod_fields(schema_match.group(1))
                    for zf in zod_fields:
                        if not any(f.name == zf.name for f in fields):
                            fields.append(zf)

        if fields:
            forms.append(FormInfo(
                id=generate_id(),
                file=file,
                component=component,
                fields=fields,
                submit_endpoint=self._find_submit(content),
                validation_lib=validation_lib,
            ))

        return forms

    def _extract_tanstack_form(self, content: str, file: str) -> list[FormInfo]:
        """Extract TanStack Form forms."""
        forms = []
        comp = re.search(r"(?:function|const)\s+(\w+)", content)
        component = comp.group(1) if comp else None

        fields = []

        # TanStack Form uses form.Field
        for m in re.finditer(r'form\.Field\s*\(\s*\{\s*name\s*:\s*[\'"](\w+)[\'"]', content):
            name = m.group(1)
            if not any(f.name == name for f in fields):
                fields.append(FormField(
                    name=name,
                    field_type=self._infer_type(name),
                ))

        if fields:
            forms.append(FormInfo(
                id=generate_id(),
                file=file,
                component=component,
                fields=fields,
                submit_endpoint=self._find_submit(content),
                validation_lib="tanstack-form",
            ))

        return forms

    def _extract_server_action_form(self, content: str, file: str) -> list[FormInfo]:
        """Extract Next.js Server Action forms."""
        forms = []
        comp = re.search(r"(?:function|const)\s+(\w+)", content)
        component = comp.group(1) if comp else None

        fields = []

        # Look for FormData.get() calls in server action
        for m in re.finditer(r'formData\.get\s*\(\s*[\'"](\w+)[\'"]', content):
            name = m.group(1)
            if not any(f.name == name for f in fields):
                fields.append(FormField(
                    name=name,
                    field_type=self._infer_type(name),
                ))

        # Also check for form inputs referencing the action
        for m in re.finditer(r'<input[^>]*name\s*=\s*[\'"](\w+)[\'"]', content):
            name = m.group(1)
            if not any(f.name == name for f in fields):
                fields.append(FormField(
                    name=name,
                    field_type=self._infer_type(name),
                ))

        if fields:
            forms.append(FormInfo(
                id=generate_id(),
                file=file,
                component=component,
                fields=fields,
                submit_endpoint="server-action",
                validation_lib="server-action",
            ))

        return forms

    def _parse_zod_fields(self, schema_body: str) -> list[FormField]:
        """Parse form fields from Zod schema body."""
        fields = []
        zod_type_map = {
            "string": "text", "number": "number", "boolean": "checkbox",
            "email": "email", "url": "url", "date": "date",
        }

        for m in re.finditer(r'(\w+)\s*:\s*z\.(\w+)\(\)', schema_body):
            field_name = m.group(1)
            zod_type = m.group(2).lower()
            field_type = zod_type_map.get(zod_type, "text")

            # Check for email() or url() modifiers
            if "email()" in schema_body[m.end():m.end()+20]:
                field_type = "email"
            elif "url()" in schema_body[m.end():m.end()+20]:
                field_type = "url"

            is_optional = ".optional()" in schema_body[m.end():m.end()+20]

            fields.append(FormField(
                name=field_name,
                field_type=field_type,
                required=not is_optional,
            ))

        return fields


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
