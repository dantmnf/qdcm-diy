## FeatureType 2 - ApplyPccFeature

```cpp
struct PccFeature {
    double unknown1[2];
    double r2r;
    double g2r;
    double b2r;
    double unknown2[8];
    double r2g;
    double g2g;
    double b2g;
    double unknown3[8];
    double r2b;
    double g2b;
    double b2b;
    double unknown4[7];
}

static_assert(sizeof(PccFeature) == 272)
```

## FeatureType 3 - Apply3DLutFineModeFeature

```cpp
struct LUT3D {
    uint32_t unknwon[3];
    uint32_t size = 4913;
    struct {
        uint32_t inR; // 0-4096, inclusive
        uint32_t inG;
        uint32_t inB;
        uint32_t outR;
        uint32_t outG;
        uint32_t outB;
    } lut[17*17*17];
}

static_assert(sizeof(LUT3D) == 117928)

```

## FeatureType 8 - ApplyGlobalGCLutFeature (Regamma LUT)
```cpp
struct GCLUT{
    uint32_t unknown = 1;
    uint32_t size = 1024;
    uint32_t unknown1 = 6;
    uint32_t red[1024]; // 10 bits
    uint32_t green[1024];
    uint32_t blue[1024];
}

static_assert(sizeof(IGCLUT) == 12300)
```

## FeatureType 7 - ApplyIgcLutFeature (Degamma LUT)

```cpp
struct IGCLUT{
    uint32_t unknown = 0;
    uint32_t size = 256;
    uint32_t unknown1 = 6;
    uint32_t red[1024]; // 12 bits
    uint32_t green[1024];
    uint32_t blue[1024];
}

static_assert(sizeof(IGCLUT) == 12300)
```

## Other

|FeatureType| name |
|-----------|-|
| 6 | ApplyMixerGCLutFeature |
| 14 | ApplyPAV2FeaturesAll |
| 20 | ApplyDitherFeature |
| 22 | ApplyPADitherFeature |
| 23 | ApplyDEFeature |
| 28 | ApplyHDRFeature |
| 29 | ApplyGameBlobFeature |
