// The return values are optional since they have to be a float4

main(float3 pos : SV_Position, float3 nrm : NORMAL, float4 diff : COLOR, float2, uv1 : TEXCOORD0, float2 uv2 : TEXCOORD1)
{
    // Technically u and v are just x and y respectively so they can be used anywhere and swizzled
    tex0.uv = uv1.uv;
    tex1.vu = uv2.vv;

    float4 neg1 = float4(-1.0f, -1.0f, -1.0f, 1.0f);

    // Unlike the pixel shader, I don't think there's much restriction on splitting/swizzling
    float4 myVar = nrm.yxz * neg1;
    float4 var2 = exp2(nrm.xyz);

    return WorldToView(pos);
}

// For the pixel shader, the type of the parameters is optional since they have to be float4
psMain(tex0, tex1, tex2)
{
    float4 myVar = lerp(tex0, tex1, tex1.a);
    myVar = saturate(dot(tex0, tex0));
    myVar = saturate(myVar + tex0);
    float4 l = tex2 * SHADOW;
    l = saturate(l + AMBIENT);
    return myVar * l;
}
