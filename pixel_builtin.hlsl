///////////////////////
// Intrinsic Functions
///////////////////////

float4 mad(a, b, c)
{
    asm {
        mad %0, %1, %2, %3
    }
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
        dp%tn0  %0, %1, %2
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

HFunc("dot", "dp%tn1\t%0, %1, %2", 1.2), HFunc("dot", "dp3\t%0, %1, %2", 1.1, 1.1), HFunc("lerp", "lrp\t%0, %3, %2, %1"), HFunc("mad", "mad\t%0, %1, %2, %3"), HFunc("fma", "mad\t%0, %1, %2, %3"), HFunc("normalize", "dp3_sat\t%z, %1_bx2, %1_bx2\nmad\t%0, %1_bias, 1-%z, %1_bx2")]