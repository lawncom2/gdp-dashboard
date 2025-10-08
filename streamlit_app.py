"""Streamlit app that helps users craft Naver-style blog posts."""

from __future__ import annotations

import colorsys
import hashlib
import io
import random
import zipfile
from textwrap import fill, wrap

from PIL import Image, ImageDraw, ImageFont
import streamlit as st


st.set_page_config(
    page_title="네이버 블로그 글 작성 비서",
    page_icon="📝",
)


def _split_keywords(raw_keywords: str) -> list[str]:
    """Split user supplied keywords into a cleaned list."""

    parts = [keyword.strip() for keyword in raw_keywords.split(",") if keyword.strip()]
    return parts[:8]  # keep it manageable for generation


def _pick_random(options: list[str]) -> str:
    """Return a random element or empty string if none provided."""

    return random.choice(options) if options else ""


def build_outline(topic: str, keywords: list[str], target_reader: str, section_count: int) -> list[str]:
    """Create a simple outline tailored to the topic and reader."""

    base_points = [
        f"{topic} 소개와 첫인상",
        f"{target_reader}에게 전하는 핵심 포인트",
        f"실생활에 적용하는 {topic} 꿀팁",
        "마무리 및 다음 이야기 예고",
    ]

    keyword_points = [f"{keyword} 제대로 활용하기" for keyword in keywords]
    combined = base_points[:-1] + keyword_points + [base_points[-1]]

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique_points = []
    for point in combined:
        if point not in seen:
            unique_points.append(point)
            seen.add(point)

    return unique_points[: max(section_count, 1)]


def _tone_prefix(tone: str) -> str:
    tone_map = {
        "일상적인": "편하게 이야기하듯",
        "전문적인": "신뢰감을 주는 어투로",
        "감성적인": "감수성 가득한 표현으로",
        "유머러스": "재미있는 비유와 함께",
    }
    return tone_map.get(tone, "자연스럽게")


def _transition_phrase() -> str:
    transitions = [
        "무엇보다도",
        "솔직히 말해서",
        "생각해 보면",
        "그래서",
        "한편",
        "덕분에",
        "조금 더 들여다보면",
        "그중에서도",
    ]
    return _pick_random(transitions)


def _ending_phrase() -> str:
    endings = [
        "오늘의 이야기가 작은 영감이 되길 바라요.",
        "읽어 주셔서 감사하고, 여러분의 생각도 궁금해요!",
        "도움이 되셨다면 공감과 이웃 추가 잊지 마세요 :)",
        "다음 포스팅에서도 유익한 이야기로 돌아올게요.",
    ]
    return _pick_random(endings)


def compose_section(topic: str, outline_point: str, tone: str, reader: str, memo: str) -> str:
    """Generate a human-like paragraph for the given outline point."""

    intro_options = [
        f"{_tone_prefix(tone)} {outline_point.lower()} 이야기를 꺼내 볼게요.",
        f"{reader}라면 한 번쯤 궁금했을 {outline_point.lower()}에 대해 이야기해요.",
        f"제가 {outline_point.lower()}를 경험하면서 느낀 솔직한 생각을 나눌게요.",
    ]
    detail_options = [
        f"{_transition_phrase()} {topic}을(를) 준비하면서 가장 크게 느낀 건 바로 '{outline_point}'였어요.",
        f"{_transition_phrase()} 사소해 보여도 {outline_point}만 잘 챙기면 분위기가 확 달라지더라고요.",
        f"{_transition_phrase()} {reader}의 입장에서 보면 {outline_point}가 왜 중요한지 금방 와닿을 거예요.",
    ]
    memo_sentence = memo.strip()
    if memo_sentence:
        memo_sentence = f"{_transition_phrase()} 제 메모에 적어 둔 것처럼 {memo_sentence}"

    closing_options = [
        f"결국 {outline_point} 덕분에 {topic}이(가) 한층 특별해졌답니다.",
        f"이 작은 습관을 더해 보시면 {reader}에게도 분명 좋은 변화가 찾아올 거예요.",
        f"하나씩 실천하다 보면 {outline_point}이(가) 자연스럽게 자리 잡게 될 거예요.",
    ]

    sentences = [
        _pick_random(intro_options),
        _pick_random(detail_options),
    ]

    if memo_sentence:
        sentences.append(memo_sentence)

    sentences.append(_pick_random(closing_options))

    paragraph = " ".join(sentences)
    return fill(paragraph, width=70)


def compose_article(
    topic: str,
    outline: list[str],
    tone: str,
    reader: str,
    memo: str,
    keywords: list[str],
    intro_style: str,
) -> tuple[str, list[str]]:
    """Build a complete draft article using the outline and tone."""

    intro_templates = {
        "하루 기록": f"오늘도 {topic}에 대해 기록을 남겨 보려고 해요. {reader}와 함께 나누고 싶은 순간들이 많아서 특히 설레는 마음으로 키보드를 두드렸답니다.",
        "정보 공유": f"{reader}에게 꼭 소개하고 싶은 {topic} 이야기를 정리해 봤어요. 직접 경험하며 챙겨 본 팁이니 천천히 따라와 주세요.",
        "리뷰": f"최근에 경험한 {topic}을(를) 솔직하게 풀어볼까 해요. 좋은 점도, 아쉬운 점도 모두 담아봤으니 참고가 되길 바라요.",
    }

    intro = intro_templates.get(intro_style, intro_templates["정보 공유"])
    intro_paragraph = fill(intro, width=70)

    body_paragraphs: list[str] = []
    for point in outline:
        body_paragraphs.append(
            compose_section(topic, point, tone, reader, memo)
        )

    keyword_sentence = ""
    if keywords:
        keyword_sentence = fill(
            f"이번 글에서 다룬 키워드는 {', '.join(keywords)} 입니다. 검색 이웃분들도 쉽게 찾으실 수 있도록 자연스럽게 녹여 두었어요.",
            width=70,
        )

    closing = fill(_ending_phrase(), width=70)

    draft = "\n\n".join(
        [intro_paragraph, *body_paragraphs, keyword_sentence, closing]
    ).strip()

    return draft, body_paragraphs


def _color_from_text(seed_text: str) -> tuple[int, int, int]:
    """Create a pleasant RGB color derived from text input."""

    digest = hashlib.md5(seed_text.encode("utf-8")).hexdigest()
    hue = int(digest[:2], 16) / 255
    saturation = 0.55 + (int(digest[2:4], 16) / 255) * 0.35
    value = 0.75 + (int(digest[4:6], 16) / 255) * 0.2
    r, g, b = colorsys.hsv_to_rgb(hue, min(saturation, 0.9), min(value, 0.95))
    return tuple(int(channel * 255) for channel in (r, g, b))


def build_image_prompt(
    topic: str, outline_point: str, tone: str, keywords: list[str]
) -> str:
    """Draft a Korean prompt for generating an image matching the section."""

    keyword_phrase = ""
    if keywords:
        keyword_phrase = f", 키워드: {', '.join(keywords[:3])}"

    prompt = (
        f"{topic} 주제의 '{outline_point}' 단락을 표현한 장면, "
        f"분위기는 {tone} 느낌으로 자연광, 사람의 시선이 머무는 구도{keyword_phrase}."
    )
    return prompt


def render_prompt_image(title: str, prompt: str) -> Image.Image:
    """Render a simple illustrative image for the prompt using Pillow."""

    base_color = _color_from_text(title + prompt)
    width, height = 900, 600
    image = Image.new("RGB", (width, height), color=base_color)

    overlay = Image.new("RGBA", (width, height))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(
        [(0, 0), (width, height)],
        fill=(255, 255, 255, 60),
    )
    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(image)
    title_font = ImageFont.load_default()
    prompt_font = ImageFont.load_default()

    wrapped_title = "\n".join(wrap(title, width=24))
    wrapped_prompt = "\n".join(wrap(prompt, width=36))

    draw.text((40, 40), wrapped_title, font=title_font, fill=(20, 20, 20))
    draw.text(
        (40, 150),
        wrapped_prompt,
        font=prompt_font,
        fill=(35, 35, 35),
        spacing=6,
    )

    return image


def initialise_state() -> None:
    """Ensure Streamlit session state keys exist."""

    for key in (
        "outline",
        "draft",
        "paragraphs",
        "images",
        "image_prompts",
        "keywords",
    ):
        st.session_state.setdefault(key, None)


def main() -> None:
    initialise_state()

    st.title("📝 네이버 블로그 글 작성 비서")
    st.caption("사람이 쓴 듯 자연스러운 흐름으로, 오늘의 이야기를 완성해 보세요.")

    with st.sidebar:
        st.header("글 설정")
        topic = st.text_input("주제", placeholder="예: 서울 성수동 카페 투어")
        target_reader = st.text_input(
            "타깃 독자",
            value="20~30대 직장인",
            help="누구에게 말하듯 글을 쓸지 정해 보세요.",
        )
        raw_keywords = st.text_input(
            "키워드 (쉼표로 구분)",
            placeholder="성수동 카페, 브런치, 디저트 추천",
        )
        tone = st.selectbox(
            "글 분위기",
            ["일상적인", "전문적인", "감성적인", "유머러스"],
        )
        intro_style = st.radio(
            "도입부 스타일",
            ["정보 공유", "하루 기록", "리뷰"],
        )
        section_count = st.slider(
            "본문 섹션 수",
            min_value=3,
            max_value=7,
            value=4,
        )
        memo = st.text_area(
            "디테일 메모",
            placeholder="강조하고 싶은 디테일이나 에피소드를 적어 주세요.",
            height=120,
        )

    keywords = _split_keywords(raw_keywords)
    st.session_state.keywords = keywords

    st.subheader("1단계 · 아웃라인 잡기")
    st.write(
        "주제와 키워드를 기반으로 자연스러운 흐름의 목차를 만들어 드릴게요."
    )

    if st.button("아웃라인 생성", use_container_width=True):
        if not topic:
            st.warning("주제를 먼저 입력해 주세요.")
        else:
            st.session_state.outline = build_outline(
                topic=topic,
                keywords=keywords,
                target_reader=target_reader,
                section_count=section_count,
            )

    if st.session_state.outline:
        st.success("아웃라인이 준비되었어요. 필요하다면 아래에서 수정해 주세요.")
        editable_outline = []
        for index, point in enumerate(st.session_state.outline, start=1):
            value = st.text_input(
                f"섹션 {index}",
                value=point,
                key=f"outline_{index}",
            )
            if value:
                editable_outline.append(value)

        st.session_state.outline = [point for point in editable_outline if point]

    st.divider()

    st.subheader("2단계 · 초안 완성")
    st.write(
        "수정한 아웃라인을 기반으로 네이버 블로그에 어울리는 문장을 구성합니다."
    )

    if st.button("초안 생성", type="primary", use_container_width=True):
        if not topic or not st.session_state.outline:
            st.warning("주제와 아웃라인을 먼저 준비해 주세요.")
        else:
            draft, paragraphs = compose_article(
                topic=topic,
                outline=st.session_state.outline,
                tone=tone,
                reader=target_reader,
                memo=memo,
                keywords=keywords,
                intro_style=intro_style,
            )
            st.session_state.draft = draft
            st.session_state.paragraphs = paragraphs
            st.session_state.images = None
            st.session_state.image_prompts = None

    if st.session_state.draft:
        st.success("초안이 생성되었습니다. 마음껏 다듬어 보세요!")
        st.text_area(
            "생성된 초안",
            value=st.session_state.draft,
            height=400,
        )

        st.download_button(
            "텍스트로 다운로드",
            data=st.session_state.draft,
            file_name=f"{topic}_네이버블로그초안.txt",
            mime="text/plain",
        )

        st.info(
            "Tip · 마무리에 이웃 소통 유도 문장을 추가하면 블로그 체류 시간이 늘어나요."
        )

        st.divider()

        st.subheader("3단계 · 단락별 이미지 만들기")
        st.write(
            "각 단락에 어울리는 장면을 묘사한 프롬프트와 시각 초안을 만들어 드려요."
        )

        if st.button("이미지 프롬프트 생성", use_container_width=True):
            if not st.session_state.paragraphs:
                st.warning("먼저 초안을 생성해 주세요.")
            else:
                generated_images: list[dict[str, object]] = []
                generated_prompts: list[str] = []
                for index, outline_point in enumerate(st.session_state.outline, start=1):
                    prompt = build_image_prompt(
                        topic=topic,
                        outline_point=outline_point,
                        tone=tone,
                        keywords=st.session_state.keywords or [],
                    )
                    image = render_prompt_image(outline_point, prompt)
                    buffer = io.BytesIO()
                    image.save(buffer, format="PNG")
                    generated_images.append(
                        {
                            "title": outline_point,
                            "bytes": buffer.getvalue(),
                            "filename": f"section_{index:02d}.png",
                        }
                    )
                    generated_prompts.append(prompt)

                st.session_state.images = generated_images
                st.session_state.image_prompts = generated_prompts

        if st.session_state.images:
            for index, (image_info, prompt) in enumerate(
                zip(st.session_state.images, st.session_state.image_prompts),
                start=1,
            ):
                st.image(
                    image_info["bytes"],
                    caption=f"섹션 {index} · {image_info['title']}",
                    use_column_width=True,
                )
                st.caption(prompt)

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as archive:
                for image_info in st.session_state.images:
                    archive.writestr(image_info["filename"], image_info["bytes"])
            zip_buffer.seek(0)

            st.download_button(
                "이미지 ZIP 다운로드",
                data=zip_buffer,
                file_name=f"{topic}_단락별이미지.zip",
                mime="application/zip",
            )


if __name__ == "__main__":
    main()
