# GTA VI clip business: plan

Written 2026-11-10. GTA VI is scheduled for 19 November 2026 on PS5 and Xbox Series X|S; PC is
expected later. Figures marked "estimate" are planning numbers, not measurements.

## 1. The short version

The opportunity is real, but the version in the original brief (20 accounts auto-reposting the
top 20 streamers, fully hands-off, ad revenue rolling in) does not make money. Three facts kill it:

| Assumption | What is actually true |
|---|---|
| Reposted clips earn ad revenue | YouTube's reused-content policy denies monetisation to channels of other people's clips without significant added value, and it applies even with the creator's permission. Shorts ad revenue is also small: roughly $0.03-$0.15 per 1,000 views. |
| More accounts = more money | Posting the same clips across many accounts on one platform is spam under every platform's rules. Accounts are linked by device, payment and content fingerprint; when one is terminated the rest usually go with it. |
| Streamers' videos are free to use | They are the streamer's copyright. Three copyright strikes terminates a YouTube channel. The legal route is a clipping programme or written permission, which also happens to be where the money is. |

What does work is the business clippers are actually paid for: **streamers and their sponsors pay
per view for clips posted under a campaign.** Typical rate is about $1 per 1,000 views (observed
range $0.50-$1.50, roughly 7% platform fee, usually capped per clip and limited by campaign budget).
That is 10-30x what Shorts ads pay, it comes with permission, and it scales with volume, which is
exactly what automation is good at.

## 2. Business model

Revenue, in order of importance:

1. **Campaign payouts** (Whop Content Rewards, Vyro, ClipAffiliates, streamers' own Discord
   programmes). Paid per verified view. Primary income from week 1.
2. **Direct retainers.** Once a brand has proof of reach, offer mid-size GTA streamers (5k-50k
   concurrent viewers, no clipping team) a flat monthly fee plus a per-view bonus. Estimate:
   $500-$2,000 per streamer per month.
3. **Platform ad revenue.** Only on channels with real added value (commentary, ranking, editing,
   your own gameplay). Treat as a bonus that arrives after month 3.
4. **Affiliate / sponsorship** on the brand pages once they have an audience.

### Account structure: 3-4 brands x 4 platforms

This gets you 12-16 accounts without breaking multi-account rules: each brand is a distinct
channel with its own angle and its own clips, present once on each platform.

| Brand (example) | Angle | YouTube Shorts | TikTok | Instagram Reels | Facebook Reels |
|---|---|---|---|---|---|
| viceclips | funniest fails and chaos | x | x | x | x |
| leonidarp | roleplay server moments | x | x | x | x |
| sixstunts | stunts, chases, own gameplay | x | x | x | x |
| (4th, later) | news, secrets, guides | x | x | x | x |

A clip belongs to exactly one brand and is posted once per platform. The pipeline enforces this.

### Illustrative monthly numbers (estimates)

| Total monthly views | Campaign payouts (~$0.5-1/1k after caps) | Shorts ads on eligible channels | Rough total |
|---|---|---|---|
| 1M | $500-$1,000 | ~$50-$100 | $0.5k-$1.1k |
| 10M | $4,000-$8,000 | ~$500-$1,000 | $4.5k-$9k |
| 50M | $15,000-$35,000 | ~$2,500-$5,000 | $17k-$40k |

Views are not guaranteed. Most new accounts see a few hundred views per clip for weeks; launch
month is the best window there will be because search demand for GTA VI will be at its peak.
Campaign budgets run out and rates drop as more clippers pile in, so income is lumpy.

Running costs (estimate): $100-$300 per month for a server, transcription, LLM calls and a
scheduling tool. One-off: a console and the game if you record your own footage.

## 3. The system

```
feeds -> watch -> ingest -> highlights -> AI package -> render 9:16 -> review queue -> publish
          (new      (licensed   (audio       (title,        (blur fill,    (you approve)   (caps, no
          uploads)   only)       spikes)      caption,       captions,                      duplicates)
                                              keep/skip)     credit)
```

Built in this repo as `clipfarm/`. See the README for commands.

| Stage | Tool | Notes |
|---|---|---|
| Detect new uploads | YouTube channel Atom feeds | Free, no API key. Poll every 5-10 min. Twitch/Kick: use their official APIs. |
| Download | yt-dlp | Refuses any source without a recorded licence. |
| Find moments | ffmpeg + numpy loudness analysis | Finds sustained spikes over the stream's own baseline. |
| Transcribe | faster-whisper | Word timings for captions and for the AI step. |
| Title, caption, filter | Claude API | Also drops clips that spoil story endings or contain slurs. |
| Render | ffmpeg | 1080x1920, blurred fill, burned captions, source credit, loudness normalised. |
| Review | CLI queue | Nothing posts until approved. |
| Publish | Official APIs | YouTube Data API implemented. TikTok Content Posting API and Instagram Graph API need app review first; until then use a scheduler (Metricool, Buffer, Later) or post manually. |
| Hosting | Any small VPS + cron | `clipfarm watch` every 10 min, `clipfarm publish --live` hourly. |

Commercial alternatives for the middle of the pipeline if you would rather pay than run code:
OpusClip, Eklipse, StreamLadder, Vizard.

## 4. What "passive" realistically means

Fully unattended posting is the fastest way to lose the accounts: one bad clip (a slur, a story
spoiler, a claim from a streamer who did not opt in) costs a strike. The realistic target is
**20-30 minutes a day**: skim the queue, approve the good ones, and once a week submit view counts
to campaigns and check for new ones. Everything else runs on its own.

Things only you can do, because they need your identity and signature:
- create the accounts and the Google Cloud / TikTok / Meta developer apps
- join campaigns and accept their terms; get paid (tax details, payout account)
- sign anything with a streamer

## 5. Risks

| Risk | Mitigation |
|---|---|
| Rockstar/Take-Two policy: gameplay video is tolerated for non-commercial use; ending, cutscene-only and "big reveal" videos are removed, with no stated end date. | No story endings or isolated cutscenes, especially in launch month. Prefer online/RP/sandbox moments. The AI filter and review step exist for this. |
| Copyright strike from a streamer | Only licensed sources; keep the proof in `license_ref`. |
| YouTube API uploads forced private | New API projects must pass YouTube's compliance audit before uploads can be public. Apply in week 1; post manually meanwhile. |
| Campaign fraud rules | Never buy views. Campaigns claw back payouts and ban accounts. |
| Platform dependence | Four platforms, several brands, several campaigns. Build an email list or Discord per brand. |
| Saturation | Everyone has this idea for launch week. The edge is speed (clip within an hour of upload) and a clear angle per brand. |

## 6. 30-day launch plan

**Before launch (now to 18 Nov)**
- Create 3 brands on 4 platforms; warm them up with GTA VI trailer-reaction and GTA Online clips from campaigns that are live today.
- Join 5-10 clipping campaigns; list each in `config/sources.json` with its URL as `license_ref`.
- Create the Google Cloud project and submit the YouTube API audit; apply for TikTok and Meta app review.
- Deploy the pipeline on a VPS; run it end to end on one licensed source.

**Launch week (19-26 Nov)**
- Record your own gameplay daily for the stunts brand (the only content that is fully yours and ad-eligible).
- 3-4 posts per brand per platform per day. Review the queue twice a day.

**Weeks 2-4**
- Kill the weakest angle, double the strongest. Track views per clip per source.
- Pitch 20 mid-size streamers a retainer using your first two weeks of numbers.
- Add commentary or ranking formats to one brand to qualify for ad revenue.
