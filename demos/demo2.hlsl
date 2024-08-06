// The actually serious shader

// The vertex shader can be called VertexShader, vsMainD3D9, vsMain, or just main
float4 vsMainD3D9(float3 pos : POSITION, float3 nrm : NORMAL, float4 diff : COLOR, float2 uv : TEXCOORD)
{
    // The UVs are just passed through to 2D textures
    colour.uv = uv.xy;
    dirt.uv = uv.xy;

    // Cubemaps use a direction to sample the texture instead of x and y.
    lighting.xyz = LocalToWorld(nrm);

    // There's no reflect instruction so you'll have to write that code yourself or take it from the original shader and wrap it in an asm{}
    specular.xyz = mySuperAwesomeReflectFunction(nrm);

    // Also you can pass some extra data to the pixel shader through colour registers.
    // These will be interpolated between vertices to get the value in the pixel shader
    // FRESNEL and BLEND are your scalar values, AMBIENT and EXTRA are your colour values.
    FRESNEL = mySuperAwesomeFresnelFunction(nrm);
    // The blend comes from the COLOR input
    BLEND = diff.a;
    // I'm still figuring out the constants related to the ambient calculations
    AMBIENT = pos.zzz;
    EXTRA = nrm;

    return WorldToView(pos);
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
