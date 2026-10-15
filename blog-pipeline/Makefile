# Korea-Asia Business Bridge 블로그 — 공통 작업 명령어
# 사용법: make <target>

.PHONY: help serve build generate filter post clean

# 기본 타겟: 도움말 출력
help:
	@echo "사용 가능한 명령어:"
	@echo ""
	@echo "  make serve          Hugo 로컬 서버 실행 (http://localhost:1313)"
	@echo "  make build          Hugo 프로덕션 빌드 (public/ 생성)"
	@echo "  make generate       Claude API로 포스트 자동 생성 (랜덤 주제)"
	@echo "  make generate TOPIC='MLCC 공급망'   주제 지정 생성"
	@echo "  make generate LANG=ko               한국어 전용 생성"
	@echo "  make filter FILE=content/posts/xxx.md  키워드 필터 단독 실행"
	@echo "  make post TOPIC='주제' LANG=both    생성+필터 한번에 실행"
	@echo "  make clean          빌드 결과물 삭제"
	@echo ""

TOPIC ?=
LANG  ?= both
FILE  ?=

# Hugo 로컬 개발 서버 (draft 포함 표시)
serve:
	hugo server -D --bind 0.0.0.0 --port 1313

# 프로덕션 빌드
build:
	hugo --minify

# Claude API 포스트 생성
generate:
	@if [ -z "$(ANTHROPIC_API_KEY)" ]; then \
		echo "오류: ANTHROPIC_API_KEY 환경변수를 설정하세요."; \
		echo "  export ANTHROPIC_API_KEY=sk-ant-..."; \
		exit 1; \
	fi
	@if [ -n "$(TOPIC)" ]; then \
		python scripts/generate_post.py --topic "$(TOPIC)" --lang $(LANG); \
	else \
		python scripts/generate_post.py --lang $(LANG); \
	fi

# AdSense 키워드 필터
filter:
	@if [ -z "$(FILE)" ]; then \
		echo "사용법: make filter FILE=content/posts/파일명.md"; \
		exit 1; \
	fi
	python scripts/keyword_filter.py "$(FILE)"

# 생성 + 필터 파이프라인 (수동 실행용)
post:
	@if [ -z "$(ANTHROPIC_API_KEY)" ]; then \
		echo "오류: ANTHROPIC_API_KEY 환경변수를 설정하세요."; \
		exit 1; \
	fi
	@$(eval POST_OUTPUT := $(shell \
		if [ -n "$(TOPIC)" ]; then \
			python scripts/generate_post.py --topic "$(TOPIC)" --lang $(LANG); \
		else \
			python scripts/generate_post.py --lang $(LANG); \
		fi \
	))
	@POST_PATH=$$(python scripts/generate_post.py --lang $(LANG) 2>/dev/null | grep POST_PATH | cut -d= -f2); \
	if [ -n "$$POST_PATH" ]; then \
		echo "필터 검사 중: $$POST_PATH"; \
		python scripts/keyword_filter.py "$$POST_PATH"; \
	fi

# 빌드 결과물 삭제
clean:
	rm -rf public/ resources/_gen/ .hugo_build.lock
