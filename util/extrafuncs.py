import math

ABBREVIATIONS = ['', 'K', 'M', 'B', 'T']
ABBREVIATION_DICT = {
    '' : 1,
    'k' : 1000,
    'm' : 1000000,
    'mil' : 1000000,
    'b' : 1000000000,
    'bil' : 1000000000,
    't' : 1000000000000,
    'tril' : 1000000000000
}

def roundSig(n):
    if n == 0:
        return 0, 0
    power = int(math.floor(math.log10(abs(n))))
    if power < 1:
        power = 0
        return round(n, 2), power
    return round(n, 4 - int(math.floor(math.log10(abs(n)))) - 1), power

def shortenNum(n):
    n, power = roundSig(n)
    if power // 3 == 0:
        return str(n)
    if power > 14:
        return "{:.3e}".format(n)
    return str(n / (10 ** (power // 3 * 3))) + ABBREVIATIONS[power // 3]
