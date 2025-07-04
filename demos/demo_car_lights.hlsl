// pro_car_lights template
// Original shader from the game

#define ONE "c15.z"

float4 VertexShader(float3 pos : POSITION, float3 nrm : NORMAL, float2 uv : TEXCOORD)
{
    // passthru texture coords
    colour.uv = uv.uv;
    glow.uv = uv.uv;

    // rotate normal
    float4 worldNormal;
    worldNormal.xyz = RotateToWorld(nrm);
    diffuse.xyz = worldNormal;

    // SH lighting
    worldNormal.w = ONE;

    float3 inAmbient;
    inAmbient.x = dot(worldNormal, PLANEX);
    inAmbient.y = dot(worldNormal, PLANEY);
    inAmbient.z = dot(worldNormal, PLANEZ);

    // gamma correction
    AMBIENT.x = sqrt(inAmbient.x);
    AMBIENT.y = sqrt(inAmbient.y);
    AMBIENT.z = sqrt(inAmbient.z);

    // project position
    return LocalToScreen(pos);
}

#define overlightingLimiter "c1"

float4 PixelShader(colour, diffuse, glow)
{
    float4 var;

    // = diffuse + ambient
    var.rgb = mad(diffuse.a, SHADOW, AMBIENT) / 2;

    // passthru alpha
    meanwhile var.a = colour.a;

    // limit overlighting
    var.rgb = saturate(var * LIMITER);
    var.rgb = saturate(var * LIMITER.a);

    // Modulate texel color
    var.rgb = saturate(x2(var * colour));

    // Premultipy
    var.rgb = var * var.a;
    var.rgb = saturate(var + glow);

    return var;
}