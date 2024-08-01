// The return values are optional since they have to be a float4

main(float3 pos : SV_Position, float3 nrm : NORMAL, float4 diff : COLOR, float2, uv1 : TEXCOORD0, uv2 : TEXCOORD1)
{
    tex0.uv = TEXCOORD0.xy;
    tex1.uv = TEXCOORD1.xy;

    float4 neg1 = float4(-1.0f, -1.0f, -1.0f, 1.0f);

    // Unlike the pixel shader, I don't think there's much restriction on splitting/swizzling
    float4 myVar = nrm.yxz * neg1;
    float4 var2 = exp2(nrm.xyz);
}

// For the pixel shader, the type of the parameters is optional since they have to be float4
psMain(tex0, tex1, tex2)
{
    float4 myVar = lerp(idk, thatone, thatone.a);
    myVar = saturate(dot(idk, idk));
    myVar = saturate(myVar + idk);
    float4 l = theseVariablesCanBeNamedAnythingOnlyTheOrderDeterminesWhichTextureTheyAre * SHADOW;
    l = saturate(l + AMBIENT);
    return myVar * l;
}