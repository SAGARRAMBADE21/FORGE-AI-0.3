"""Manager for external service integrations."""

import logging
from dataclasses import dataclass
from enum import Enum

from core.types import FrontendAnalysis

logger = logging.getLogger(__name__)


class IntegrationType(str, Enum):
    PAYMENT = "payment"
    EMAIL = "email"
    STORAGE = "storage"
    ANALYTICS = "analytics"
    AI_ML = "ai_ml"


@dataclass
class IntegrationConfig:
    """Configuration for an integration."""

    type: IntegrationType
    provider: str
    env_vars: list[str]
    dependencies: list[str]


class IntegrationManager:
    """Detect and generate integrations."""

    def __init__(self):
        pass

    async def detect_integrations(
        self, analysis: FrontendAnalysis
    ) -> list[IntegrationConfig]:
        """Detect required integrations from frontend analysis."""
        integrations = []

        # Detect from API calls
        for api in analysis.api_calls:
            endpoint = api.endpoint.lower()

            # Payment
            if any(
                word in endpoint
                for word in ["payment", "checkout", "stripe", "billing"]
            ):
                integrations.append(
                    IntegrationConfig(
                        type=IntegrationType.PAYMENT,
                        provider="stripe",
                        env_vars=["STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"],
                        dependencies=["stripe"],
                    )
                )

            # Storage
            if any(word in endpoint for word in ["upload", "file", "image", "media"]):
                integrations.append(
                    IntegrationConfig(
                        type=IntegrationType.STORAGE,
                        provider="s3",
                        env_vars=[
                            "AWS_ACCESS_KEY_ID",
                            "AWS_SECRET_ACCESS_KEY",
                            "S3_BUCKET",
                        ],
                        dependencies=["@aws-sdk/client-s3"],
                    )
                )

        # Deduplicate
        seen = set()
        unique = []
        for integration in integrations:
            key = (integration.type, integration.provider)
            if key not in seen:
                seen.add(key)
                unique.append(integration)

        return unique

    def generate_integration_code(
        self, integration: IntegrationConfig
    ) -> dict[str, str]:
        """Generate code for an integration."""
        if (
            integration.type == IntegrationType.PAYMENT
            and integration.provider == "stripe"
        ):
            return self._generate_stripe()
        elif (
            integration.type == IntegrationType.STORAGE and integration.provider == "s3"
        ):
            return self._generate_s3()
        elif integration.type == IntegrationType.EMAIL:
            return self._generate_email(integration.provider)

        return {}

    def _generate_stripe(self) -> dict[str, str]:
        """Generate Stripe integration."""
        return {
            "src/integrations/stripe.ts": """
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2023-10-16',
});

export async function createPaymentIntent(
  amount: number,
  currency: string = 'usd'
): Promise<Stripe.PaymentIntent> {
  return stripe.paymentIntents.create({
    amount,
    currency,
  });
}

export async function createCustomer(
  email: string,
  name?: string
): Promise<Stripe.Customer> {
  return stripe.customers.create({
    email,
    name,
  });
}

export async function handleWebhook(
  body: string,
  signature: string
): Promise<Stripe.Event> {
  return stripe.webhooks.constructEvent(
    body,
    signature,
    process.env.STRIPE_WEBHOOK_SECRET!
  );
}

export { stripe };
""",
        }

    def _generate_s3(self) -> dict[str, str]:
        """Generate S3 integration."""
        return {
            "src/integrations/storage.ts": """
import { S3Client, PutObjectCommand, GetObjectCommand, DeleteObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';

const s3 = new S3Client({
  region: process.env.AWS_REGION || 'us-east-1',
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
  },
});

const BUCKET = process.env.S3_BUCKET!;

export async function uploadFile(
  key: string,
  body: Buffer,
  contentType: string
): Promise<string> {
  await s3.send(new PutObjectCommand({
    Bucket: BUCKET,
    Key: key,
    Body: body,
    ContentType: contentType,
  }));

  return `https://${BUCKET}.s3.amazonaws.com/${key}`;
}

export async function getSignedDownloadUrl(
  key: string,
  expiresIn: number = 3600
): Promise<string> {
  const command = new GetObjectCommand({
    Bucket: BUCKET,
    Key: key,
  });

  return getSignedUrl(s3, command, { expiresIn });
}

export async function deleteFile(key: string): Promise<void> {
  await s3.send(new DeleteObjectCommand({
    Bucket: BUCKET,
    Key: key,
  }));
}

export { s3 };
""",
        }

    def _generate_email(self, provider: str) -> dict[str, str]:
        """Generate email integration."""
        if provider == "sendgrid":
            return {
                "src/integrations/email.ts": """
import sgMail from '@sendgrid/mail';

sgMail.setApiKey(process.env.SENDGRID_API_KEY!);

export interface EmailOptions {
  to: string;
  subject: string;
  text?: string;
  html?: string;
  templateId?: string;
  dynamicTemplateData?: Record<string, any>;
}

export async function sendEmail(options: EmailOptions): Promise<void> {
  await sgMail.send({
    from: process.env.EMAIL_FROM!,
    ...options,
  });
}

export async function sendTemplateEmail(
  to: string,
  templateId: string,
  data: Record<string, any>
): Promise<void> {
  await sgMail.send({
    from: process.env.EMAIL_FROM!,
    to,
    templateId,
    dynamicTemplateData: data,
  });
}
""",
            }

        return {}
