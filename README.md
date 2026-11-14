# Brand demo repo

One repo for all your demos. When a brand wants a demo you change **only the brief (the prompt) and the images**, run one workflow,
and get a zip with **3 posts, a carousel, a Reel, captions and hashtags**.

## For each new brand (about 5 minutes)
1. Open `brand/prompt.txt` and replace the text with the new brand's brief, in plain words: brand name, handle, phone, tagline, what they sell, products and their real benefits, offers (or "none"), language, tone, season, special requests, things to avoid. `brand/BRAND_INTAKE.md` is the checklist to send the client.
2. Replace `brand/assets/logo.png` with the brand's logo.
3. Delete the old files in `brand/assets/products/` and add the new product images. Name the files after the products (for example `wall_paint.png`) and mention the file names in the brief so each product is matched.
   - A transparent PNG is best. A product on a plain white or flat-colour background is cut out automatically (check the edges), or run `python tools/cutout.py in.jpg out.png`.
4. **Actions, Build brand demo, Run workflow.** Download the zip from the run's Artifacts.

You do not set colours: they are read from the logo (or taken from the brief if you write "colours: ..."). The AI reads the brief and writes all the text.

Once per repo: add the secret `GEMINI_API_KEY` (Settings, Secrets and variables, Actions; a free key from Google AI Studio works).

## What is in the zip
| File | What it is |
|---|---|
| `post_1_hero.jpg`, `post_2_offer.jpg`, `post_3_tips.jpg` | 3 feed posts |
| `carousel_1.jpg` ... `carousel_5.jpg` | 5-slide carousel |
| `reel.mp4` | 15 to 20 second Reel (animated text and product pop-ins; silent, or with a voice) |
| `captions_and_hashtags.txt` | Caption for each item plus hashtags |
| `preview.jpg` | One-page contact sheet |
| `CHECK_BEFORE_SENDING.txt` | Automatic warnings: banned words, numbers or phone numbers that are not in the brief |
| `copy.json` | All the text, so you can edit it |

The structured profile the AI read from your brief is saved as `output/brand_profile_generated.json`.

## Keeping several brands in the same repo (optional)
Make `brands/acme/`, `brands/zeta/` and so on, each with `prompt.txt` and `assets/`. In the workflow, type `brands/acme` in the **brand** box.
Use a private repo, because it holds client logos and product images.

## Options
- Voice: `--voice none|edge|elevenlabs` (default none). `edge` is free but sounds like a computer voice and clients notice it. A text-only Reel with licensed music is often better for a demo.
- Music: put royalty-free `.mp3` files in `assets/music/`. Never use copyrighted songs.
- Local run: `pip install -r requirements.txt`, then `python demo.py check` and `python demo.py build` (ffmpeg needed for the Reel). Other flags: `--brand folder`, `--no-reel`, `--offline`.
- Manual control: if `brand/brand.json` exists it is used instead of the brief (see `examples/brand.json.example`). A `demo_copy` block in it replaces the AI text.

## Rules built in
- The AI may only use products, offers, numbers and the phone number from the brief. Anything else is flagged in `CHECK_BEFORE_SENDING.txt`.
- No cartoon or film characters, celebrities, politicians, religious figures for selling, or fake giveaways.
- A demo is not for posting on the client's page until they approve it.
- Always look at every image and the Reel before sending. Check spelling (especially Hindi, Bengali, Marathi) and product image quality.

## Project layout
```
brand/             prompt.txt, assets/logo.png, assets/products/*   <- the only things you change per brand
demo.py            command line (check, build)
kit/               profile.py (brief -> profile), copy.py (text + checks), posts.py, reel.py, common.py
fonts/             Poppins, Noto Sans Devanagari and Bengali (open licence)
```
To change how the posts look for every brand, edit `hero`, `offer` and `tips` in `kit/posts.py`.
