"""Send a synthetic fixture to Groq and print only validated structured output.

Run from apps/api:
    .venv/bin/python -m scripts.smoke_groq
"""

from __future__ import annotations

import asyncio
import json

from app.core.config import Settings
from app.integrations.groq_client import GroqClient, GroqError, GroqProviderError, GroqTemporaryError
from app.modules.analysis.schemas import AnalysisPrompt


async def main() -> None:
    settings = Settings()
    if not settings.groq_is_configured:
        print("Groq smoke check failed: GROQ_API_KEY and GROQ_MODEL must be set in .env.")
        raise SystemExit(1)

    print("Sending a synthetic fixture to Groq.", flush=True)
    client = GroqClient(settings)
    fixture = AnalysisPrompt(
        uploaded_evidence=(
            "Document ID: 11111111-1111-1111-1111-111111111111.\n"
            "Passage ID: 22222222-2222-2222-2222-222222222222.\n"
            "Passage: Payment receipt received. Possession remains disputed."
        ),
        lawyer_context="Focus review on payment and possession records.",
    )
    try:
        result = await client.analyze_case(fixture)
    except GroqTemporaryError as error:
        print(f"Groq smoke check failed: {error.safe_message} ({error.reason})")
        raise SystemExit(1) from error
    except GroqProviderError as error:
        print(f"Groq smoke check failed: {error.safe_message} (provider returned HTTP {error.status_code})")
        raise SystemExit(1) from error
    except GroqError as error:
        print(f"Groq smoke check failed: {error.safe_message}")
        raise SystemExit(1) from error
    finally:
        await client.close()

    print("Groq smoke check passed. Validated output:")
    print(json.dumps(result.model_dump(mode="json"), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
