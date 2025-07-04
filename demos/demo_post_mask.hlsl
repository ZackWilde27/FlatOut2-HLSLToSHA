// post_mask template
// Original shader from the game

const string inputStreamFormat = "PosprojTex4";

#define TINT "c3"

#pconstants 4

float4 PixelShader(float4 colour, float4 alpha)
{
    float4 c;

    c.rgb = colour;
    meanwhile c.a = alpha.a * TINT.a;

    return c;
}

Technique T0
{
    Pass P0
    {
        AddressU[0] = Clamp;
        AddressV[0] = Clamp;
        MagFilter[0] = Linear;

        AddressU[1] = Clamp;
        AddressV[1] = Clamp;
        MagFilter[1] = Linear;
    }
}