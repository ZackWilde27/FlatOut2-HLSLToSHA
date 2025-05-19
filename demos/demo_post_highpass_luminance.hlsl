// post_highpass_luminance template
// Original shader from the game, with the original comments too

#pconstants 6

const string inputStreamFormat = "PosprojTex4";

#define weights "c5"
#define scale "c4"
#define cutoff "c3"

float4 PixelShader(float4 colour)
{
    float4 lum;

    // OLD: Convert to luminance (C5 = RGB component weights)
    //lum = dot(colour, weights);

    // luminance should already be in the source alpha, just copy to all components
    lum.rgb = colour.a;
    meanwhile lum.a = colour.a;

    // Cut-off
    lum -= cutoff;

    // Scaling
    return lum * scale * 4;
}
