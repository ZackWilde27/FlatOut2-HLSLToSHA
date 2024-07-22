// The actually serious shader
float4 PixelShader(float4 colour, float4 specular, float4 dirt, float4 lighting)
{
    float4 c = specular * FRESNEL;
    c = saturate(c + colour);
    float4 l = lighting * SHADOW;
    l = saturate(l + AMBIENT);
    return c * l;
}