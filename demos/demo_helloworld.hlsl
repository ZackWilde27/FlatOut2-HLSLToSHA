// The most basic shader possible

float4 VertexShader(float3 pos : SV_Position)
{
    return WorldToScreen(pos);
}

float4 PixelShader()
{
    float4 blue = float4(0.0f, 0.0f, 1.0f, 1.0f);
    return blue;
}
