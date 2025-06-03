// post_box4 template
// The original shader was written in actual HLSL, so I pretty much just ported it

float4 PixelShader(float4 Tex0, float4 Tex1, float4 Tex2, float4 Tex3)
{
    // Average all 4 samples together to do a box blur
    return Tex0 + Tex1 + Tex2 + Tex3 * 0.25f;
}