/**
 * Light Tower Group — Claude-powered intake chatbot
 * Netlify Function: /.netlify/functions/chat
 *
 * Environment variable required (set in Netlify dashboard):
 *   ANTHROPIC_API_KEY = your key from scripts/.env
 */

const SYSTEM_PROMPT = `You are the mandate intake assistant for Light Tower Group, a New York-based institutional commercial real estate capital advisory firm founded by Ben Rohr.

Light Tower Group places debt and equity for complex CRE mandates nationwide:
- Senior debt, bridge loans, construction financing, CMBS, agency lending (Fannie/Freddie/FHA), life company financing
- Joint venture equity, preferred equity, mezzanine financing, co-GP capital
- Investment advisory: acquisitions, dispositions, recapitalizations
- Minimum mandate: typically $5M+. Compensation is fully success-based — no retainers, no upfront fees.
- Deep NYC focus, national coverage, 250,000+ capital source relationships

Your job: have a natural, professional conversation to understand the visitor's deal, then connect them with Ben.

Conversation flow — ask these ONE AT A TIME, naturally:
1. Start: ask what they're working on (open-ended)
2. Clarify: capital type (debt / equity / both / advisory)
3. Asset type and location
4. Deal size (approximate)
5. Timeline
6. Once you understand the deal: ask for their name and email so Ben can follow up

Rules:
- Maximum 2-3 sentences per response. Be direct and sharp — this audience reads 10-Ks.
- Never mention rates, pricing, or approval likelihood — that's Ben's job.
- Never list all your questions at once. One at a time.
- If they ask about fees: "Fully success-based — you pay nothing unless and until we close."
- If they ask about deal size minimums: "We typically start at $5M but evaluate every deal on its merits."
- If they seem to be exploring or not ready: stay helpful and informative, don't push.
- When you have their name and email: tell them Ben Rohr will be in touch personally within one business day.
- Sign off warm but brief.`;

exports.handler = async (event) => {
  // Handle CORS preflight
  if (event.httpMethod === 'OPTIONS') {
    return {
      statusCode: 200,
      headers: {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
      },
      body: '',
    };
  }

  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method not allowed' };
  }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    return {
      statusCode: 500,
      headers: { 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ error: 'API key not configured' }),
    };
  }

  let messages;
  try {
    ({ messages } = JSON.parse(event.body));
  } catch {
    return { statusCode: 400, body: JSON.stringify({ error: 'Invalid request body' }) };
  }

  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 300,
        system: SYSTEM_PROMPT,
        messages,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      console.error('Anthropic API error:', data);
      return {
        statusCode: 502,
        headers: { 'Access-Control-Allow-Origin': '*' },
        body: JSON.stringify({ error: 'Upstream API error' }),
      };
    }

    return {
      statusCode: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
      body: JSON.stringify({ reply: data.content[0].text }),
    };
  } catch (err) {
    console.error('Function error:', err);
    return {
      statusCode: 500,
      headers: { 'Access-Control-Allow-Origin': '*' },
      body: JSON.stringify({ error: 'Internal error' }),
    };
  }
};
