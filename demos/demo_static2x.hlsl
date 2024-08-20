// static2x template

float4 VertexShader(float3 pos : SV_Position, float4 diff : COLOR, float2 uv : TEXCOORD)
{
    AMBIENT = diff.xyz
    FRESNEL = diff.a;
    colour.uv = uv;
    
    return WorldToView(pos);
}

float4 PixelShader(colour)
{
    float4 c = saturate(x2(colour * AMBIENT));
    // There's no way to add the "+" prefix to an instruction, I'm working on it
    c.a = colour * AMBIENT;
    return c;
}