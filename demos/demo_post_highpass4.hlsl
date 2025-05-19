// post_highpass4 template
// Original shader from the game

#define threshold "c3"
#define scaling "c4"

#pconstants 5

float4 PixelShader(float4 sample1, float4 sample2, float4 sample3, float4 sample4)
{
    // Average all 4 samples together
    // (a + b / 2) == lerp(a, b, 0.5)
    float4 s1 = sample1 + sample2 / 2;
    float4 s2 = sample3 + sample4 / 2;

    s1 = s1 + s2 / 2;

    s1 -= threshold;

    return s1 * scaling * 4;
}