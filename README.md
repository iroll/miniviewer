# miniviewer
a very lightweight, cross-platform image viewer

WHY: HEIF/HEIC support in Windows is obnoxiously broken and may require kicking Microsoft a couple bucks for the codec to use MS Photos.

* Maybe it's my personal computer and I don't want to give them more money
* Maybe it's my work computer and I don't want to deal with IT to get the codec or install an alternative to Photos
* Maybe the alternatives are bloated with feature creep and I just need to quickly flip some photo folders 

But if you're lucky and have access to python, the pillow-heif package solves this pretty easy and you may be able to do an end-run around other annoyances. Miniviewer is a very simple photo viewer that was vibed out to address the irritation of getting a codec error every time Photos tried to open a heic file.
