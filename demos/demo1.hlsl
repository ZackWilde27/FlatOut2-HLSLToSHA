// The most basic shader possible

float4 VertexShader(float3 pos : POSITION)
{
    return WorldToView(pos);
}

float4 PixelShader()
{
    float4 red = float4(1.0f, 0.0f, 0.0f, 1.0f);
    return red;
}
