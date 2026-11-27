# Publishing to YouTube (SWC Trading), tested 26 Nov 2026

Channel: SWC Trading, id UCsmDVXhrXBPqSFjsD7xBerQ. Rick is signed in to it in the Claude desktop app's built-in browser.
Rick asked for these to be published publicly and automatically. Use the built-in browser tools (mcp__remote-devices__Claude_Browser__*).
Never sign in or out, and never change channel settings.

## 1. Host the file on GitHub (Studio fetches it from there)
- In the cloud workspace: call add_repo {owner: "SaveWithCrypto", repo: "swc-videos", access: "push"}, then
  `git clone --depth 1 https://github.com/SaveWithCrypto/swc-videos /home/claude/swc-videos` (10 min timeout).
- Delete files in `videos/` older than 10 days (`git rm`) to keep the repo small.
- Copy the new files into `videos/`, then commit with `git -c user.name="Claude" -c user.email="noreply@anthropic.com" commit -m "<msg>"`, ending the message with the attribution lines from the session's system reminder if one is given.
- Push: `git -c push.negotiate=true push origin HEAD:main`.
- Raw URL: `https://raw.githubusercontent.com/SaveWithCrypto/swc-videos/main/videos/<filename>`. Wait about 20 s, then check it with fetch from the Studio tab: it should return status 200 and the right content-length.

## 2. Upload the video
1. `navigate` the Studio tab to `https://studio.youtube.com/channel/UCsmDVXhrXBPqSFjsD7xBerQ/videos/upload?d=ud`.
2. Run with javascript_tool (after a 3 s wait):
```js
const r = await fetch(RAW_URL); const blob = await r.blob();
const file = new File([blob], FILENAME, {type: 'video/mp4'});
const input = document.querySelector('input[type=file][name=Filedata]');
const dt = new DataTransfer(); dt.items.add(file); input.files = dt.files;
input.dispatchEvent(new Event('change', {bubbles: true}));
```
3. Title. A script can't set it, and cmd+a doesn't work. Instead:
   - Select the existing text with javascript_tool: `const el=document.querySelector('#title-textarea #textbox'); el.focus(); const s=getSelection(); const rg=document.createRange(); rg.selectNodeContents(el); s.removeAllRanges(); s.addRange(rg);`
   - Then use computer `key` "Backspace", then computer `type` with the title (max 100 characters).
   - Check it with `document.querySelector('#title-textarea #textbox').innerText`.
4. Description: `find` the textbox "Tell viewers about your video", `left_click` it, then computer `type` the description. Do it the same way as the title if it isn't empty.
5. Thumbnail (main video only): with javascript_tool, fetch the raw PNG URL into a File (type image/png), set it on `input#file-loader` the same way as above, and dispatch `change`. A button named "thumbnail.png" then appears. Shorts don't take custom thumbnails, so skip this for them.
6. With javascript_tool, click `tp-yt-paper-radio-button[name=VIDEO_MADE_FOR_KIDS_NOT_MFK]`. Then `find` "Show more" and left_click it, and click the radios `VIDEO_HAS_ALTERED_CONTENT_YES` and `VIDEO_PAID_PRODUCT_PLACEMENT_NO`. Check that each has aria-checked="true".
7. With javascript_tool, click `#next-button` 3 times, 1.5 s apart, then click `tp-yt-paper-radio-button[name=PUBLIC]`.
8. Wait for YouTube's checks. Poll `document.querySelector('ytcp-video-upload-progress').innerText` every ~30 s (up to 10 min) until it contains "Checks complete".
   - If it reports a copyright or other issue, do NOT publish. Click `tp-yt-paper-radio-button[name=PRIVATE]`, then `#done-button`, and report it.
   - If a "We're still checking your content" dialog appears, click "Got it" and keep waiting.
9. Click `#done-button`. Success means `ytcp-video-share-dialog` text contains "Video published" and a `https://youtu.be/...` link (read it from that dialog's text). Close the dialog with `ytcp-video-share-dialog #close-button`.

Shorts use the same steps: YouTube treats a vertical video under 3 minutes as a Short automatically. Put #Shorts at the end of the description.

## 3. Community post (morning only)
Note: Studio works with the browser panel hidden, but the main youtube.com site only renders while the browser panel is showing in the Claude app. If the posts page stays blank (document.body.innerText is empty after ~15 s), skip the post. Put the post text and poll in the email, ready to paste, and say the browser panel was hidden.
1. `navigate` to `https://www.youtube.com/channel/UCsmDVXhrXBPqSFjsD7xBerQ/posts`, then wait 4 s.
2. `find` "Give a shoutout", left_click it, and computer `type` the post text, including the new video's youtu.be link.
3. `find` "Add a text poll". There are two matches; left_click the one that's on screen (the later ref; if one is "outside the viewport", use the other).
4. `find` "Add option": fill the two textboxes (left_click, then type). Click "Add another option", run `find` "Add option" again, and fill the new third textbox.
5. `find` "Post": left_click the visible `button "Post"` (the later ref). A "Post created" toast confirms it.
