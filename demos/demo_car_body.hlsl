// The actually serious shader

// The vertex shader can be called VertexShader, vsMainD3D9, vsMain, or just main
float4 vsMainD3D9(float3 pos : POSITION, float3 nrm : NORMAL, float4 diff : COLOR, float2 uv : TEXCOORD)
{
    // The UVs are just passed through to 2D textures
    colour.uv = uv.xy;
    dirt.uv = uv.xy;

    // Cubemaps use a direction to sample the texture instead of x and y.
    float3 worldNormal = LocalToWorld(nrm)
    lighting.xyz = worldNormal;

    // Calculate the reflection vector for the specular cubemap
    float4 incident = pos - CAMERA;
    incident = normalize(incident);
    specular.xyz = reflect(incident, worldNormal);

    // Also you can pass some extra data to the pixel shader through colour registers.
    // These will be interpolated between vertices to get the value in the pixel shader
    // FRESNEL and BLEND are your scalar values, AMBIENT and EXTRA are your colour values.
    FRESNEL = mySuperAwesomeFresnelFunction(nrm);
    // The blend comes from the COLOR input
    BLEND = diff.a;

    // Doesn't do anything, I just haven't implemented declaring yet.
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

// The pixel shader can be called PixelShader, psMainD3D9, or psMain
float4 psMainD3D9(float4 colour, float4 specular, float4 dirt, float4 lighting)
{
    float4 c = specular * FRESNEL;
    c = saturate(c + colour);
    float4 l = lighting * SHADOW;
    l = saturate(l + AMBIENT);
    return c * l;
}
