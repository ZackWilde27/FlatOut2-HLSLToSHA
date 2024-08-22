// static2x template

float4 VertexShader(float3 pos : SV_Position, float4 diff : COLOR, float2 uv : TEXCOORD)
{
    AMBIENT = diff.xyz
    FRESNEL = diff.a;
    colour.uv = uv.uv;
    
    return WorldToScreen(pos);
}

float4 PixelShader(colour)
{
    float4 c;
    c.rgb = saturate(x2(colour * AMBIENT));
    meanwhile c.a = colour * AMBIENT;
    return c;
}
