# generation/prompts/devops/__init__.py
"""
DevOps Prompts
"""

from .cicd_prompt import CICD_PROMPT
from .cloud_aws_prompt import CLOUD_AWS_PROMPT
from .cloud_azure_prompt import CLOUD_AZURE_PROMPT
from .cloud_gcp_prompt import CLOUD_GCP_PROMPT
from .docker_prompt import DOCKER_PROMPT
from .kubernetes_prompt import KUBERNETES_PROMPT
from .monitoring_prompt import MONITORING_PROMPT
from .terraform_prompt import TERRAFORM_PROMPT

DEVOPS_PROMPTS = {
    "docker": DOCKER_PROMPT,
    "kubernetes": KUBERNETES_PROMPT,
    "cicd": CICD_PROMPT,
    "terraform": TERRAFORM_PROMPT,
    "cloud_aws": CLOUD_AWS_PROMPT,
    "cloud_gcp": CLOUD_GCP_PROMPT,
    "cloud_azure": CLOUD_AZURE_PROMPT,
    "monitoring": MONITORING_PROMPT,
}

__all__ = [
    "DEVOPS_PROMPTS",
    "DOCKER_PROMPT",
    "KUBERNETES_PROMPT",
    "CICD_PROMPT",
    "TERRAFORM_PROMPT",
    "CLOUD_AWS_PROMPT",
    "CLOUD_GCP_PROMPT",
    "CLOUD_AZURE_PROMPT",
    "MONITORING_PROMPT",
]
