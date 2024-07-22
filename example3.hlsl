float4 PixelShader(float4 idk, float4 thatone, float4 theseVariablesCanBeNamedAnythingOnlyTheOrderDeterminesWhichTextureTheyAre)
{
    float4 myVar = lerp(idk, thatone, thatone.a);
    myVar = saturate(dot(idk, idk));
    myVar = saturate(myVar + idk);
    float4 l = theseVariablesCanBeNamedAnythingOnlyTheOrderDeterminesWhichTextureTheyAre * SHADOW;
    l = saturate(l + AMBIENT);
    return myVar * l;
}