// post_combine2 template
// Original shader from the game

// This will not allow the compiler to combine the last two instructions into a mad,
// making it output the exact same code as the original
#python noOptimizations = True

#define tint1 "c3"
#define tint2 "c4"

#pconstants 5

float4 PixelShader(float4 image1, float4 image2)
{
    image1 *= tint1;
    image2 *= tint2;
    return image1 + image2;
}