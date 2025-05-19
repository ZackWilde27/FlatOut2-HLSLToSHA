// pro_racemap template
// Original shader from the game

float4 VertexShader(float3 pos : POSITION, float2 uv1 : TEXCOORD0, float2 uv2 : TEXCOORD1)
{
    colour.uv = uv1.xy;
    alpha.uv = uv2.xy;

    return LocalToScreen(pos);
}

float4 PixelShader(float4 colour, float4 alpha)
{
    float4 c;

    c.rgb = colour;
    meanwhile c.a = colour.a * alpha.a;

    return c;
}