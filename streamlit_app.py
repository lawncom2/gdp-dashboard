import re
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="선거 연락 운영 통제 MVP",
    page_icon="📣",
    layout="wide",
)

KST = ZoneInfo("Asia/Seoul")


def now_kst() -> datetime:
    return datetime.now(tz=KST)


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("82") and len(digits) >= 11:
        digits = "0" + digits[2:]
    return digits


def is_valid_phone(raw: str) -> bool:
    return bool(re.fullmatch(r"0\d{9,10}", normalize_phone(raw)))


def can_call_now(ts: datetime) -> bool:
    # 안내 기준: 선거운동 기간 내 06:00~23:00, 직접 통화 방식
    start, end = time(6, 0), time(23, 0)
    return start <= ts.timetz().replace(tzinfo=None) <= end


def add_audit(action: str, target: str, detail: str, actor: str = "admin") -> None:
    st.session_state.audit_logs = pd.concat(
        [
            st.session_state.audit_logs,
            pd.DataFrame(
                [
                    {
                        "timestamp": now_kst().strftime("%Y-%m-%d %H:%M:%S %Z"),
                        "actor": actor,
                        "action": action,
                        "target": target,
                        "detail": detail,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )


if "contacts" not in st.session_state:
    st.session_state.contacts = pd.DataFrame(
        columns=["id", "name", "phone", "region", "tags", "consent", "opt_out", "source", "created_at"]
    )

if "sms_templates" not in st.session_state:
    st.session_state.sms_templates = pd.DataFrame(
        [
            {
                "name": "기본 인사",
                "content": "안녕하세요 {name}님, [캠프명]입니다. 오늘 일정 안내드립니다.",
            }
        ]
    )

if "call_scripts" not in st.session_state:
    st.session_state.call_scripts = pd.DataFrame(
        [
            {
                "name": "기본 통화 스크립트",
                "script": "안녕하세요 {name}님, [후보명] 캠프입니다. 1분만 시간 괜찮으실까요?",
                "checklist": "본인 확인\n통화 동의 확인\n핵심 메시지 전달\n추가 문의 응대\n거부 시 즉시 종료",
            }
        ]
    )

if "sms_queue" not in st.session_state:
    st.session_state.sms_queue = pd.DataFrame(
        columns=["contact_id", "name", "phone", "template", "message", "status", "blocked_reason", "queued_at"]
    )

if "audit_logs" not in st.session_state:
    st.session_state.audit_logs = pd.DataFrame(
        columns=["timestamp", "actor", "action", "target", "detail"]
    )

st.title("📣 선거 연락 운영 통제형 MVP")
st.caption(
    "이 앱은 내부 운영/통제용 프로토타입입니다. 실제 대량 발송 기능은 포함하지 않으며, 동의·수신거부·시간 제한 준수를 우선합니다."
)

with st.expander("⚖️ 준수 체크포인트", expanded=True):
    st.markdown(
        """
- 연락처는 **최소 수집**, **목적 내 이용**, **종료 후 파기** 원칙으로 관리하세요.
- **수신거부(Opt-out)** 대상은 문자/전화 대상에서 즉시 제외하세요.
- 전화 운영은 기본적으로 **직접 통화**, **시간 제한(06:00~23:00)** 기준을 적용하세요.
- 자동동보통신/실발송은 별도 법률 검토 및 공식 발송 서비스 계약 후 연동하세요.
        """
    )


contacts_tab, sms_tab, call_tab, audit_tab = st.tabs(
    ["1) 연락처 관리", "2) 문자 캠페인", "3) 전화 스크립트", "4) 이력·감사 로그"]
)

with contacts_tab:
    st.subheader("연락처 등록")
    with st.form("add_contact"):
        c1, c2, c3 = st.columns(3)
        with c1:
            name = st.text_input("이름", placeholder="홍길동")
            phone = st.text_input("전화번호", placeholder="010-1234-5678")
        with c2:
            region = st.text_input("지역", placeholder="천안")
            tags = st.text_input("태그(쉼표 구분)", placeholder="지지자,행사참석")
        with c3:
            consent = st.checkbox("동의 확인", value=True)
            opt_out = st.checkbox("수신거부", value=False)
            source = st.selectbox("정보 출처", ["자발적 제공", "기존 후원자 DB", "행사 신청", "기타"])

        submitted = st.form_submit_button("연락처 추가")
        if submitted:
            if not name.strip():
                st.error("이름을 입력하세요.")
            elif not is_valid_phone(phone):
                st.error("전화번호 형식이 올바르지 않습니다. (예: 01012345678)")
            else:
                next_id = 1 if st.session_state.contacts.empty else int(st.session_state.contacts["id"].max()) + 1
                new_row = {
                    "id": next_id,
                    "name": name.strip(),
                    "phone": normalize_phone(phone),
                    "region": region.strip(),
                    "tags": tags.strip(),
                    "consent": consent,
                    "opt_out": opt_out,
                    "source": source,
                    "created_at": now_kst().strftime("%Y-%m-%d %H:%M:%S"),
                }
                st.session_state.contacts = pd.concat(
                    [st.session_state.contacts, pd.DataFrame([new_row])], ignore_index=True
                )
                add_audit("CONTACT_CREATED", str(next_id), f"{name} / consent={consent}, opt_out={opt_out}")
                st.success(f"연락처 #{next_id}가 추가되었습니다.")

    st.subheader("연락처 목록")
    if st.session_state.contacts.empty:
        st.info("등록된 연락처가 없습니다.")
    else:
        view_df = st.session_state.contacts.copy()
        view_df["발송가능"] = view_df["consent"] & (~view_df["opt_out"])
        st.dataframe(view_df, use_container_width=True)

        eligible = view_df[view_df["발송가능"]]
        st.metric("발송 가능 대상", len(eligible))

with sms_tab:
    st.subheader("문자 템플릿 관리")
    with st.form("new_template"):
        template_name = st.text_input("템플릿 이름", placeholder="일정 안내")
        template_content = st.text_area(
            "템플릿 내용",
            placeholder="안녕하세요 {name}님, [캠프명]입니다...",
            height=120,
        )
        t_submitted = st.form_submit_button("템플릿 저장")
        if t_submitted:
            if not template_name.strip() or not template_content.strip():
                st.error("템플릿 이름과 내용을 입력하세요.")
            else:
                st.session_state.sms_templates = pd.concat(
                    [
                        st.session_state.sms_templates,
                        pd.DataFrame([{"name": template_name.strip(), "content": template_content.strip()}]),
                    ],
                    ignore_index=True,
                )
                add_audit("SMS_TEMPLATE_CREATED", template_name.strip(), "template saved")
                st.success("템플릿이 저장되었습니다.")

    st.dataframe(st.session_state.sms_templates, use_container_width=True)

    st.subheader("캠페인 대기열 생성")
    if st.session_state.contacts.empty:
        st.warning("먼저 연락처를 등록하세요.")
    else:
        t_names = st.session_state.sms_templates["name"].tolist()
        selected_template = st.selectbox("사용 템플릿", t_names)

        regions = sorted([r for r in st.session_state.contacts["region"].dropna().unique() if r])
        selected_regions = st.multiselect("대상 지역(미선택 시 전체)", regions)

        only_eligible = st.toggle("동의+비거부 대상만 포함", value=True)

        if st.button("대기열 만들기"):
            template_text = st.session_state.sms_templates.loc[
                st.session_state.sms_templates["name"] == selected_template, "content"
            ].iloc[0]
            target_df = st.session_state.contacts.copy()
            if selected_regions:
                target_df = target_df[target_df["region"].isin(selected_regions)]

            queue_rows = []
            for _, row in target_df.iterrows():
                blocked_reason = ""
                if not row["consent"]:
                    blocked_reason = "동의 미확인"
                elif row["opt_out"]:
                    blocked_reason = "수신거부"

                if only_eligible and blocked_reason:
                    continue

                status = "BLOCKED" if blocked_reason else "READY"
                queue_rows.append(
                    {
                        "contact_id": row["id"],
                        "name": row["name"],
                        "phone": row["phone"],
                        "template": selected_template,
                        "message": template_text.replace("{name}", str(row["name"])),
                        "status": status,
                        "blocked_reason": blocked_reason,
                        "queued_at": now_kst().strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )

            st.session_state.sms_queue = pd.DataFrame(queue_rows)
            add_audit("SMS_QUEUE_CREATED", selected_template, f"rows={len(queue_rows)}")
            st.success(f"대기열 {len(queue_rows)}건 생성 완료")

    if not st.session_state.sms_queue.empty:
        st.dataframe(st.session_state.sms_queue, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.metric("READY", int((st.session_state.sms_queue["status"] == "READY").sum()))
        with c2:
            st.metric("BLOCKED", int((st.session_state.sms_queue["status"] == "BLOCKED").sum()))

        if st.button("실발송 시뮬레이션(로그만 기록)"):
            sent_count = int((st.session_state.sms_queue["status"] == "READY").sum())
            blocked_count = int((st.session_state.sms_queue["status"] == "BLOCKED").sum())
            add_audit("SMS_SIMULATED", "queue", f"ready={sent_count}, blocked={blocked_count}")
            st.info("실제 발송은 수행하지 않았습니다. 감사 로그만 남겼습니다.")

with call_tab:
    st.subheader("전화 스크립트 관리")
    with st.form("call_script_form"):
        script_name = st.text_input("스크립트 이름", placeholder="지지 호소 콜")
        script_text = st.text_area("통화 멘트", height=100)
        checklist = st.text_area("체크리스트(줄바꿈 구분)", height=100)
        s_submitted = st.form_submit_button("스크립트 저장")
        if s_submitted:
            if not script_name.strip() or not script_text.strip():
                st.error("스크립트 이름과 멘트는 필수입니다.")
            else:
                st.session_state.call_scripts = pd.concat(
                    [
                        st.session_state.call_scripts,
                        pd.DataFrame(
                            [
                                {
                                    "name": script_name.strip(),
                                    "script": script_text.strip(),
                                    "checklist": checklist.strip(),
                                }
                            ]
                        ),
                    ],
                    ignore_index=True,
                )
                add_audit("CALL_SCRIPT_CREATED", script_name.strip(), "script saved")
                st.success("스크립트가 저장되었습니다.")

    st.dataframe(st.session_state.call_scripts, use_container_width=True)

    st.subheader("통화 운영 기록")
    if st.session_state.contacts.empty:
        st.warning("연락처가 없어 통화 대상을 선택할 수 없습니다.")
    else:
        names = st.session_state.contacts.apply(lambda r: f"#{r['id']} {r['name']} ({r['phone']})", axis=1).tolist()
        selected_contact_label = st.selectbox("통화 대상", names)
        selected_result = st.selectbox("통화 결과", ["연결", "부재", "거절", "재통화요청"])
        note = st.text_input("메모", placeholder="요점 기록")

        now_time = now_kst()
        is_call_window = can_call_now(now_time)
        if is_call_window:
            st.success(f"현재 시각 {now_time.strftime('%H:%M')} KST: 전화 가능 시간대입니다.")
        else:
            st.error(f"현재 시각 {now_time.strftime('%H:%M')} KST: 권장 시간대(06:00~23:00) 밖입니다.")

        if st.button("통화 결과 저장"):
            add_audit("CALL_LOGGED", selected_contact_label, f"result={selected_result}; note={note}")
            st.success("통화 결과가 감사 로그에 기록되었습니다.")

with audit_tab:
    st.subheader("감사 로그")
    if st.session_state.audit_logs.empty:
        st.info("로그가 없습니다.")
    else:
        st.dataframe(
            st.session_state.audit_logs.sort_values("timestamp", ascending=False),
            use_container_width=True,
        )

        csv = st.session_state.audit_logs.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "감사 로그 CSV 다운로드",
            data=csv,
            file_name=f"audit_log_{now_kst().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
