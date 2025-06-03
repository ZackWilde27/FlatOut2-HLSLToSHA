const string inputStreamFormat = "PosprojTex1";

#define tint "c3"
#define bias(x) x - 0.5

#pconstants 4

float4 PixelShader(float4 Tex0, texreg2ar(Tex0) Tex1)
{
    float4 c = Tex0 + bias(Tex1);
    c.a = Tex0.a;

    return c;
}

Technique T0
{
    Pass P0
    {
        AddressU[0] = Clamp;
        AddressV[0] = Clamp;
        MagFilter[0] = Point;

        AddressU[1] = Clamp;
        AddressV[1] = Clamp;
        MagFilter[1] = Point;
    }
}