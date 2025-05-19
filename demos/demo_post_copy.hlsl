// post_copy template
// Original shader from the game

#pconstants 4

#define tintVal "c3";

float4 PixelShader(colour)
{
    return colour * tintVal;
}

Technique T0
{
    Pass P0
    {
        AddressU[0] = Clamp;
    	AddressV[0] = Clamp;
    	MagFilter[0] = Linear;
    }
}