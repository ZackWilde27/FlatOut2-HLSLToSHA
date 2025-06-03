// pro_sunflare template
// Original shader from the game

#define OPACITY AMBIENT

float4 VertexShader(float3 pos : POSITION, float4 diff : COLOR, float2 uv : TEXCOORD0)
{
    OPACITY.rgba = diff;

    colour.uv = uv.uv;
    brightness.uv = uv.uv;

    return LocalToScreen(pos);
}

float4 PixelShader(float4 colour, float4 brightness)
{
    float4 c;

    c.rgb = colour * brightness;
    meanwhile c.a = colour.a * OPACITY.a;

    return c;
}

Technique T0
{
    Pass P0
    {
        MinFilter[1] = Point;
        MagFilter[1] = Point;
    }
}