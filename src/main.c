/*---------------------------------------------------------------------------------

    snesgame2 - Genesis Invaders (PVSnesLib)

    Move the SNES sprite with the D-pad, fire with A/B. Sega Genesis consoles
    drop in from the top of the screen; shoot one and it flashes then vanishes.
    Press Y to set off a screen-clearing bomb.

---------------------------------------------------------------------------------*/
#include <snes.h>

#include "sprites.inc"          // player: sprites_til/_tilend, sprites_pal/_palend
#include "enemy.inc"            // enemy:  enemy_til/_tilend,   enemy_pal/_palend
#include "bullet.inc"           // bullet: bullet_til/_tilend,  bullet_pal/_palend

// Font tiles + palette, linked from data.asm
extern char tilfont, palfont;

#define SCREEN_W      256
#define ENEMY_SIZE    21        // art is 2/3 of the 32x32 cell (rest transparent)
#define PLAYER_SIZE   21
#define BULLET_SIZE   8
#define NUM_ENEMIES   5
#define NUM_BULLETS   4
#define BULLET_SPEED  4
#define FLASH_FRAMES  12        // how long a hit console blinks before it disappears
#define OFFSCREEN_Y   240       // any y >= 224 is below the visible 224-line screen
#define PLAYFIELD_TOP 24        // top 3 tile-rows (y 0..23) are the stats bar
#define SCORE_PER_KILL 100
#define START_LIVES   5
#define PLAYER_FLASH_FRAMES 60  // ~1s of blink + invulnerability after a hit

// Each gfx4snes 32x32 sprite is a 64-tile (0x400-word) block; lay them end to end.
#define VRAM_PLAYER   0x0000
#define VRAM_ENEMY    0x0400
#define VRAM_BULLET   0x0800
#define GFX_PLAYER    0x0000
#define GFX_ENEMY     0x0040    // VRAM_ENEMY  / 16
#define GFX_BULLET    0x0080    // VRAM_BULLET / 16

// Sprite palettes live at CGRAM 128, 16 entries apart.
#define PAL_ENEMY_CG  (128 + 1 * 16)
#define PAL_BULLET_CG (128 + 2 * 16)

// OAM sprite ids are the sprite index * 4.
#define OAM_PLAYER    0
#define OAM_ENEMY(i)  (((i) + 1) * 4)
#define OAM_BULLET(j) (((j) + 1 + NUM_ENEMIES) * 4)

// --- Enemy state ---
short enemyX[NUM_ENEMIES];
short enemyY[NUM_ENEMIES];      // logical y (pixels); negative = sliding in from the top
short enemySpeed[NUM_ENEMIES];           // descent speed in 1/256ths of a pixel per frame
unsigned char enemyFrac[NUM_ENEMIES];    // sub-pixel accumulator for slow movement
unsigned char enemyFlash[NUM_ENEMIES];   // >0 while playing the hit/blink animation

// --- Score ---
unsigned short score = 0;
unsigned short lastScore = 0xFFFF;       // force first HUD draw
char scoreStr[8];

// --- Player lives / state ---
unsigned char lives = START_LIVES;
unsigned char lastLives = 0xFF;          // force first HUD draw
unsigned char playerFlash = 0;           // >0 = recently hit: blinking + invulnerable
unsigned char gameOver = 0;
char livesStr[4];

// --- Bullet state ---
short bulletX[NUM_BULLETS];
short bulletY[NUM_BULLETS];
unsigned char bulletActive[NUM_BULLETS];

// --- 16-bit xorshift PRNG ---
unsigned short rngState = 0xACE1;
unsigned short rnd(void)
{
    rngState ^= rngState << 7;
    rngState ^= rngState >> 9;
    rngState ^= rngState << 8;
    return rngState;
}

// (Re)spawn an enemy above the top of the screen at a random column/speed.
void spawnEnemy(unsigned char i)
{
    short nx = (short)(rnd() & 0xFF);
    if (nx > SCREEN_W - ENEMY_SIZE) nx -= ENEMY_SIZE;   // keep fully on-screen (0..224)
    enemyX[i]     = nx;
    enemyY[i]     = -ENEMY_SIZE - (short)(rnd() & 0x7F); // staggered above the screen
    enemySpeed[i] = 100 + (rnd() & 0x3F);               // ~0.39..0.64 px/frame (was 1..2)
    enemyFrac[i]  = 0;
    enemyFlash[i] = 0;
}

// Start the hit animation on an enemy that isn't already reacting, and score it.
void hitEnemy(unsigned char i)
{
    if (enemyFlash[i] == 0)
    {
        enemyFlash[i] = FLASH_FRAMES;
        score += SCORE_PER_KILL;
    }
}

// Fire a bullet from the player's top-centre, if a slot is free.
void fireBullet(short px, short py)
{
    unsigned char j;
    for (j = 0; j < NUM_BULLETS; j++)
    {
        if (!bulletActive[j])
        {
            bulletActive[j] = 1;
            bulletX[j] = px + (PLAYER_SIZE / 2) - (BULLET_SIZE / 2);
            bulletY[j] = py - BULLET_SIZE;
            return;
        }
    }
}

// Redraw the score in the stats bar, but only when it actually changed.
void drawScore(void)
{
    if (score == lastScore) return;
    lastScore = score;
    sprintf(scoreStr, "%05u", score);
    consoleDrawText(7, 2, scoreStr);
}

// Lose SCORE_PER_KILL points (the value an un-hit kill would have earned), clamped at 0.
void penalizeScore(void)
{
    if (score >= SCORE_PER_KILL) score -= SCORE_PER_KILL;
    else                         score = 0;
}

// Redraw the remaining lives in the stats bar, only when it changed.
void drawLives(void)
{
    if (lives == lastLives) return;
    lastLives = lives;
    sprintf(livesStr, "%u", (unsigned short)lives);   // promote: 816-tcc won't widen char varargs
    consoleDrawText(24, 2, livesStr);
}

int main(void)
{
    unsigned short pad0, down0;
    unsigned char i, j;
    short x = 112, y = 170;     // player position (starts near the bottom)

    // --- Text console (uses the bundled pvsneslib font) ---
    consoleSetTextMapPtr(0x6800);
    consoleSetTextGfxPtr(0x3000);
    consoleSetTextOffset(0x0100);
    consoleInitText(0, 16 * 2, &tilfont, &palfont);

    bgSetGfxPtr(0, 0x2000);
    bgSetMapPtr(0, 0x6800, SC_32x32);
    setMode(BG_MODE1, 0);
    bgSetDisable(1);
    bgSetDisable(2);

    // --- Stats bar: top 3 rows (y 0..23), kept clear of gameplay ---
    // Row 0 lands in the overscan ZSNES crops, so keep HUD text on rows 1-2.
    consoleDrawText(6, 1, "MEGA DRIVER INVADERS");
    consoleDrawText(1, 2, "SCORE");
    consoleDrawText(18, 2, "LIVES");
    drawScore();
    drawLives();

    // --- Player gfx -> VRAM 0x0000, palette slot 0. Sizes: small 8, large 32. ---
    oamInitGfxSet(&sprites_til, (&sprites_tilend - &sprites_til),
                  &sprites_pal, (&sprites_palend - &sprites_pal),
                  0, VRAM_PLAYER, OBJ_SIZE8_L32);

    // --- Enemy + bullet gfx/palettes (loaded while the screen is still off) ---
    dmaCopyVram(&enemy_til,  VRAM_ENEMY,  (&enemy_tilend  - &enemy_til));
    dmaCopyVram(&bullet_til, VRAM_BULLET, (&bullet_tilend - &bullet_til));
    dmaCopyCGram(&enemy_pal,  PAL_ENEMY_CG,  (&enemy_palend  - &enemy_pal));
    dmaCopyCGram(&bullet_pal, PAL_BULLET_CG, (&bullet_palend - &bullet_pal));

    // Player: sprite 0, priority 3 (in front), large (32x32), palette 0
    oamSet(OAM_PLAYER, x, y, 3, 0, 0, GFX_PLAYER, 0);
    oamSetEx(OAM_PLAYER, OBJ_LARGE, OBJ_SHOW);

    // Enemies: large (32x32), palette 1
    for (i = 0; i < NUM_ENEMIES; i++)
    {
        spawnEnemy(i);
        oamSet(OAM_ENEMY(i), 0, OFFSCREEN_Y, 2, 0, 0, GFX_ENEMY, 1);
        oamSetEx(OAM_ENEMY(i), OBJ_LARGE, OBJ_SHOW);
    }

    // Bullets: small (8x8), palette 2, parked off-screen until fired
    for (j = 0; j < NUM_BULLETS; j++)
    {
        bulletActive[j] = 0;
        oamSet(OAM_BULLET(j), 0, OFFSCREEN_Y, 2, 0, 0, GFX_BULLET, 2);
        oamSetEx(OAM_BULLET(j), OBJ_SMALL, OBJ_SHOW);
    }

    setScreenOn();

    while (1)
    {
        pad0  = padsCurrent(0);
        down0 = padsDown(0);

        // Out of lives: freeze the field (sprites hold their last positions).
        if (gameOver)
        {
            WaitForVBlank();
            continue;
        }

        if (pad0 & KEY_LEFT  && x > 0)                 x -= 2;
        if (pad0 & KEY_RIGHT && x < SCREEN_W - PLAYER_SIZE) x += 2;   // 256 - 21
        if (pad0 & KEY_UP    && y > PLAYFIELD_TOP)      y -= 2;       // stay below stats bar
        if (pad0 & KEY_DOWN  && y < 224 - PLAYER_SIZE)  y += 2;       // 224 - 21

        if (down0 & (KEY_A | KEY_B)) fireBullet(x, y);

        // Y = screen-clearing bomb: detonate every console at once.
        if (down0 & KEY_Y)
            for (i = 0; i < NUM_ENEMIES; i++) hitEnemy(i);

        // Draw the player; while flashing (recently hit) blink on/off every 4 frames.
        if (playerFlash > 0) playerFlash--;
        if (playerFlash > 0 && ((playerFlash >> 2) & 1))
            oamSet(OAM_PLAYER, 0, OFFSCREEN_Y, 3, 0, 0, GFX_PLAYER, 0);
        else
            oamSet(OAM_PLAYER, x, y, 3, 0, 0, GFX_PLAYER, 0);

        // --- Move bullets up; deactivate once they leave the top edge ---
        for (j = 0; j < NUM_BULLETS; j++)
        {
            if (bulletActive[j])
            {
                bulletY[j] -= BULLET_SPEED;
                if (bulletY[j] < PLAYFIELD_TOP) bulletActive[j] = 0;   // stop at the stats bar
            }
        }

        // --- Update enemies: flashing ones freeze then respawn, others descend ---
        for (i = 0; i < NUM_ENEMIES; i++)
        {
            if (enemyFlash[i] > 0)
            {
                enemyFlash[i]--;
                if (enemyFlash[i] == 0) spawnEnemy(i);   // hit console gone, new one drops in
            }
            else
            {
                // Sub-pixel descent: accumulate 1/256ths, advance whole pixels.
                unsigned short acc = enemyFrac[i] + (unsigned short)enemySpeed[i];
                enemyY[i]   += (short)(acc >> 8);
                enemyFrac[i] = (unsigned char)(acc & 0xFF);
                if (enemyY[i] >= 224)        // escaped un-hit off the bottom
                {
                    penalizeScore();
                    spawnEnemy(i);
                }
            }
        }

        // --- Collisions: bullet (8x8) vs enemy (32x32) ---
        for (j = 0; j < NUM_BULLETS; j++)
        {
            if (!bulletActive[j]) continue;
            for (i = 0; i < NUM_ENEMIES; i++)
            {
                if (enemyFlash[i] > 0) continue;          // already hit
                if (bulletX[j] + BULLET_SIZE > enemyX[i] &&
                    bulletX[j] < enemyX[i] + ENEMY_SIZE &&
                    bulletY[j] + BULLET_SIZE > enemyY[i] &&
                    bulletY[j] < enemyY[i] + ENEMY_SIZE)
                {
                    bulletActive[j] = 0;   // bullet spent
                    hitEnemy(i);           // start flash-then-disappear
                    break;
                }
            }
        }

        // --- Collisions: player (21x21) vs enemy. Costs a life + flash; brief i-frames ---
        if (playerFlash == 0)
        {
            for (i = 0; i < NUM_ENEMIES; i++)
            {
                if (enemyFlash[i] > 0 || enemyY[i] < PLAYFIELD_TOP) continue;  // not a live target
                if (x + PLAYER_SIZE > enemyX[i] &&
                    x < enemyX[i] + ENEMY_SIZE &&
                    y + PLAYER_SIZE > enemyY[i] &&
                    y < enemyY[i] + ENEMY_SIZE)
                {
                    if (lives > 0) lives--;
                    spawnEnemy(i);                         // the console that hit us is gone (no score)
                    if (lives == 0)
                    {
                        gameOver = 1;
                        consoleDrawText(11, 13, "GAME OVER");
                    }
                    else
                    {
                        playerFlash = PLAYER_FLASH_FRAMES; // blink + invulnerable for a moment
                    }
                    break;
                }
            }
        }

        // --- Draw enemies ---
        for (i = 0; i < NUM_ENEMIES; i++)
        {
            // Hidden while still above the stats bar (keeps the top row clear),
            // or on the "off" beat of the hit blink.
            if (enemyY[i] < PLAYFIELD_TOP ||
                (enemyFlash[i] > 0 && ((enemyFlash[i] >> 1) & 1)))
                oamSet(OAM_ENEMY(i), 0, OFFSCREEN_Y, 2, 0, 0, GFX_ENEMY, 1);
            else
                oamSet(OAM_ENEMY(i), enemyX[i], (unsigned char)enemyY[i], 2, 0, 0, GFX_ENEMY, 1);
        }

        // --- Draw bullets ---
        for (j = 0; j < NUM_BULLETS; j++)
        {
            if (bulletActive[j])
                oamSet(OAM_BULLET(j), bulletX[j], (unsigned char)bulletY[j], 2, 0, 0, GFX_BULLET, 2);
            else
                oamSet(OAM_BULLET(j), 0, OFFSCREEN_Y, 2, 0, 0, GFX_BULLET, 2);
        }

        drawScore();
        drawLives();

        WaitForVBlank();
    }
    return 0;
}
