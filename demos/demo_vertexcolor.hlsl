// vertexcolor template

float4 VertexShader(float3 pos : SV_Position, float4 colour : COLOR, float2 uv : TEXCOORD)
{
    AMBIENT = colour;
    return WorldToView(pos);
}

float4 PixelShader()
{
    return AMBIENT;
}