// Generates copy-pasteable request examples for the public /api/v1 API.
// Used by the "Use in API" dialog and the Voice API documentation page.

import { getApiBaseUrl } from "@/lib/api"

export interface CodeExample {
  language: "cURL" | "JavaScript" | "Python"
  code: string
}

const KEY_PLACEHOLDER = "$OMNIVOICE_API_KEY"

/** Text-to-speech examples for a given voice id. */
export function ttsExamples(voiceId: string, text = "Hello from OmniVoice!"): CodeExample[] {
  const base = getApiBaseUrl()
  return [
    {
      language: "cURL",
      code: `curl -X POST "${base}/api/v1/text-to-speech" \\
  -H "Authorization: Bearer ${KEY_PLACEHOLDER}" \\
  -H "Content-Type: application/json" \\
  -d '{"voiceId": "${voiceId}", "text": "${text}", "format": "mp3"}' \\
  --output speech.mp3`,
    },
    {
      language: "JavaScript",
      code: `const res = await fetch("${base}/api/v1/text-to-speech", {
  method: "POST",
  headers: {
    Authorization: \`Bearer \${process.env.OMNIVOICE_API_KEY}\`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ voiceId: "${voiceId}", text: "${text}", format: "mp3" }),
});
const audio = await res.arrayBuffer();`,
    },
    {
      language: "Python",
      code: `import os, requests

res = requests.post(
    "${base}/api/v1/text-to-speech",
    headers={"Authorization": f"Bearer {os.environ['OMNIVOICE_API_KEY']}"},
    json={"voiceId": "${voiceId}", "text": "${text}", "format": "mp3"},
)
with open("speech.mp3", "wb") as f:
    f.write(res.content)`,
    },
  ]
}

/** List-voices examples (no specific voice). */
export function listVoicesExamples(): CodeExample[] {
  const base = getApiBaseUrl()
  return [
    {
      language: "cURL",
      code: `curl "${base}/api/v1/voices" \\
  -H "Authorization: Bearer ${KEY_PLACEHOLDER}"`,
    },
    {
      language: "JavaScript",
      code: `const res = await fetch("${base}/api/v1/voices", {
  headers: { Authorization: \`Bearer \${process.env.OMNIVOICE_API_KEY}\` },
});
const { voices } = await res.json();`,
    },
    {
      language: "Python",
      code: `import os, requests

res = requests.get(
    "${base}/api/v1/voices",
    headers={"Authorization": f"Bearer {os.environ['OMNIVOICE_API_KEY']}"},
)
print(res.json()["voices"])`,
    },
  ]
}
