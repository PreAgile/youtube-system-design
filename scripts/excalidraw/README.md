# Excalidraw 그림 만들기

`diagrams.mjs`에 단계별 그림을 정의하고, 실제 Excalidraw 라이브러리(`@excalidraw/excalidraw` 0.18.1)로 편집 원본과 SVG·PNG를 내보낸다.

```bash
cd scripts/excalidraw
npm install playwright        # 최초 1회. 브라우저가 없으면 npx playwright install chromium
node render.mjs ../../excalidraw   # excalidraw/src/*.excalidraw, excalidraw/exports/*.svg|png 생성
node verify.mjs ../../excalidraw   # 원본을 다시 열어 텍스트·화살표 연결·크기를 확인
```

- 설치된 브라우저 버전이 맞지 않으면 `CHROME_PATH`로 Chromium 실행 파일을 지정한다.
- 라이브러리와 글꼴은 esm.sh·unpkg에서 받으므로 네트워크가 필요하다.
- `.excalidraw` 파일은 excalidraw.com에서 열어 직접 고칠 수 있다. 직접 고친 뒤에는 그 화면에서 다시 내보낸다.
