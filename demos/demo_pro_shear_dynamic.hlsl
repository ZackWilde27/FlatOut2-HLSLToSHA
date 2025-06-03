// pro_shear_dynamic template
// Original shader from the game, within reason

#vconstants 33

#define SHEAR "c32.w"
#define ONE "c15.z"

float4 VertexShader(float3 pos : POSITION, float3 nrm : NORMAL, float2 uv : TEXCOORD0)
{
    colour.uv = uv.uv;

    // Shear position before projecting
    float4 position = pos;
    float absoluteX = abs(pos.x);
    position.y += pos.x * SHEAR;

    // The lighting cubemap can just be given the world normal
    float4 worldNormal;
    worldNormal.xyz = RotateToWorld(nrm);
    diffuse.xyz = worldNormal;

    // Ambient
    worldNormal.w = ONE;

    float3 amb;
    amb.x = sqrt(dot(worldNormal, PLANEX));
    amb.y = sqrt(dot(worldNormal, PLANEY));
    amb.z = sqrt(dot(worldNormal, PLANEZ));
    AMBIENT = amb;

    return LocalToScreen(position);
}

float4 PixelShader(float4 colour, float4 diffuse)
{
    float4 c;

    // = diffuse + ambient
    c.rgb = mad(diffuse.a, SHADOW, AMBIENT) / 2;
    // passthru alpha
    meanwhile c.a = colour.a;

    // limit overlighting
    c.rgb = saturate(c * LIMITER);
    c.rgb = saturate(c * LIMITER.a);

    // modulate texel color
    c.rgb = saturate(x2(c * colour));

    return c;
}