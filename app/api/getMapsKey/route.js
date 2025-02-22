export async function GET() {
    if (!process.env.NEXT_PUBLIC_MAPS_KEY) {
      return new Response(JSON.stringify({ error: "API key not found" }), {
        status: 500,
        headers: { "Content-Type": "application/json" },
      });
    }
  
    return new Response(
      JSON.stringify({ apiKey: process.env.NEXT_PUBLIC_MAPS_KEY }),
      {
        headers: { "Content-Type": "application/json" },
      }
    );
  }
  