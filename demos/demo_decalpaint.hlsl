// decalpaint template

// clipping planes that ultimately went unused
#define clip0 "c9"
#define clip1 "c10"

float4 VertexShader(float3 pos : SV_Position, float2 uv1 : TEXCOORD0, float2 uv2 : TEXCOORD1)
{
    tex0.uv = uv1.xy;
    tex1.uv = uv2.xy;

    return WorldToView(pos);
}

float4 PixelShader(float4 tex0, float4 tex1)
{
    // I don't have any way to texkill, so put it in assembly for now
    asm
    {
        texkill     t2
    }

    return tex0 * tex1;
}