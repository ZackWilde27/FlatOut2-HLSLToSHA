// default_dynamic template

float4 VertexShader(float3 pos : SV_Position, float2 nrm : NORMAL, float2 uv : TEXCOORD)
{
    colour.uv = uv.xy

    float4 worldNormal = RotateToWorld(nrm);
    diffuse.xyz = worldNormal;

    worldNormal.a = 1.0f;

    float3 inAmbient;
    // Still figuring out what these ambient constants mean
    // I wrote it in assembly on the main page but here's the string version
    inAmbient.x = sqrt(dot(worldNormal, "c17"));
    inAmbient.y = sqrt(dot(worldNormal, "c18"));
    inAmbient.z = sqrt(dot(worldNormal, "c19"));

    AMBIENT = inAmbient;

    return LocalToScreen(pos);
}

float4 PixelShader(float4 colour, float4 diffuse)
{
    // lighting
    float4 var;

    var.rgb = mad(diffuse.a, SHADOW, AMBIENT) / 2
    meanwhile var.a = colour.a;

    // Don't know what these are
    var = saturate(var * "c1");
    var = saturate(var * "c1.a");


    return saturate(x2(var * colour));
}
