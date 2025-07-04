// pro_car_tire template
// The original shader from the game (within reason)

VertexShader(pos : POSITION, nrm : NORMAL, uv : TEXCOORD)
{
    // rotate normal
    float4 worldNormal;
    worldNormal.xyz = RotateToWorld(nrm);

    lighting.xyz = worldNormal;

    // passthru texture coords
    colour.uv = uv;

    // SH lighting
    worldNormal.w = 1.0f;

    float3 ambient;
    ambient.x = sqrt(dot(worldNormal, PLANEX));
    ambient.y = sqrt(dot(worldNormal, PLANEY));
    ambient.z = sqrt(dot(worldNormal, PLANEZ));
    AMBIENT = ambient;

    // position -> world
    float3 worldPosition = LocalToWorld(pos);
    // compute vtx->eye ray and normalize it
    float3 incident = normalize(worldPosition - CAMERA);

    float3 BugbearReflect(float3 V, float3 N, float V_dot_N)
    {
        // R = 2*(V dot N)*N - V
        float d = V_dot_N + V_dot_N;
        return mad(N, d, -V);
    }

    // r0.w = dot(V, N)
    worldNormal.w = dot(incident, worldNormal);
    specular.xyz = BugbearReflect(incident, worldNormal, worldNormal.w);

    float4 consts = float4(0.15f, 0.5f, 1, 0);
    float f;

    // Compute fresnel term approximation
    worldNormal.w = abs(worldNormal.w);
    // complement
    worldNormal.w = 1 - worldNormal.w;
    // squared
    f = worldNormal.w * worldNormal.w;
    // quartic
    f *= f;
    // quintic
    f *= worldNormal.w;

    FRESNEL = mad(f, consts.y, consts.x);

    // passthru damage map blend factor
    EXTRA = "c22";

    // project position
    return LocalToScreen(pos);
}

// I removed the unused code and the associated comments
PixelShader(colour, specular, lighting)
{
    float4 c;
    float4 l;

    // diffuse = directional + ambient
    l.rgb = mad(lighting.a, SHADOW, AMBIENT) / 2;

    // limit overlighting
    l.rgb = saturate(l * LIMITER);
    l.rgb = saturate(l * LIMITER.a);

    // specular
    lighting.rgb = EXTRA * specular.a;

    // color = texel*diffuse
    c.rgb = saturate(x2(colour * l));

    // final blend between reflection
    c.rgb = lerp(c, specular, FRESNEL);
    c.rgb = saturate(c + lighting);
    c.a = colour;

    return c;
}