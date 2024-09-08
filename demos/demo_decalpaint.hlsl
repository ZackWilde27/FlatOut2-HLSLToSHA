// decalpaint template

// clipping planes that ultimately went unused
#define clip0 "c9"
#define clip1 "c10"

float4 VertexShader(float3 pos : SV_Position, float2 uv1 : TEXCOORD0, float2 uv2 : TEXCOORD1)
{
    tex0.uv = uv1.xy;
    tex1.uv = uv2.xy;

    // clip 0
    // float4 var1 = dot(pos, clip0.xyz);
    // float4 var2 = dot(pos, clip1.xyz);
    // tex2.x = var1.x + clip0.w;
    // tex2.y = var2.y + clip1.w;
    // tex2.z = pos.z - pos.z;

    return LocalToScreen(pos);
}

float4 PixelShader(float4 tex0, float4 tex1, texkill tex2)
{
    return tex0 * tex1;
}

Technique T0
{
    Pass P0
    {
        Zbias = 2;
    }
}
