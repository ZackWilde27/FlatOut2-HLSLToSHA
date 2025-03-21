///////////////////////
// Intrinsic Functions
///////////////////////

float4 mad(a, b, c)
{
    asm {
        mad %0, %1, %2, %3
    }
}

float4 fma(a, b, c)
{
    return mad(a, b, c);
}

float4 lerp(x, y, float s)
{
    asm {
        lrp %0, %3, %2, %1
    }
}

float dot(x, y)
{
    asm {
        dp%tn1  %0, %1, %2
    }
}

// Uses the formula from pro_water, I don't know the math behind it.
float3 normalize(float3 value)
{
    asm {
        dp3_sat %z, %1_bx2, %1_bx2
        mad %0, %1_bias, 1-%z, %1_bx2
    }
}