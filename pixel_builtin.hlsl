///////////////////////
// Intrinsic Functions
///////////////////////

float4 mad(a, b, c)
{
    asm {
	    mad	%0, %1, %2, %3
    }
}

float4 fma(a, b, c)
{
    return mad(a, b, c);
}

float4 lerp(x, y, float s)
{
    asm {
        lrp	%0, %3, %2, %1
    }
}

#ifdef float(pixelshaderversion) > 1.1
    float dot(x, y)
    {
        asm {
            dp%tn1	%0, %1, %2
        }
    }
#else
    float dot(x, y)
    {
        asm {
            dp3	%0, %1, %2
        }
    }
#endif

// Uses the formula from pro_water, I don't know the math behind it.
float3 normalize(float3 value)
{
    asm {
        dp3_sat	%z, %1_bx2, %1_bx2
        mad	%0, %1_bias, 1-%z, %1_bx2
    }
}

////////////////////////////
// Type-Building Functions
////////////////////////////

// Due to the swizzle limitations, only 3 of these can be done

float4 float4(float3 rgb, float a)
{
    "%0.rgb" = rgb;
    "%0.a" = a;
}

float4 float4(float x)
{
    return x;
}

float3 float3(float x)
{
    return x;
}