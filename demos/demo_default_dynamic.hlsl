// default_dynamic template

#define constantOne "c15.z"

float4 VertexShader(float3 pos : SV_Position, float2 nrm : NORMAL, float2 uv : TEXCOORD)
{
    colour.uv = uv.xy

    float4 worldNormal = LocalToWorld(nrm);
    diffuse.xyz = worldNormal;

    worldNormal.a = constantOne;

    float3 inAmbient;
    // Still figuring out what these ambient constants mean
    // I wrote it in assembly on the main page but here's the string version
    inAmbient.x = dot(worldNormal, "c17");
    inAmbient.y = dot(worldNormal, "c18");
    inAmbient.z = dot(worldNormal, "c19");

    inAmbient.x = sqrt(inAmbient.x);
    inAmbient.y = sqrt(inAmbient.y);
    inAmbient.z = sqrt(inAmbient.z);

    AMBIENT = inAmbient;

    return WorldToScreen(pos);
}

float4 PixelShader(float4 colour, float4 diffuse)
{
    // lighting
    float4 var = mad(diffuse.a, SHADOW, AMBIENT) / 2

    var.a = colour.a;

    // Don't know what these are
    var = saturate(var * "c1");
    var = saturate(var * "c1.a");


    return saturate(x2(var * colour));
}
