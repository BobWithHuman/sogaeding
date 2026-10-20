# 제품 소스 위치

현재 제품 구현은 시작 전이며 `app/` 모듈과 MCP 서버는 아직 없다. 이 디렉터리는 이후 `app/control/`, `app/pdp/`, `app/gateway/`, `app/executor/` 등 명세의 제품 코드를 담는다. `app/__init__.py`와 실제 실행 모듈은 구현 단계에서 추가한다.

Docker의 `dev` 서비스는 이 디렉터리와 `tests/`, `tools/`를 읽기 전용으로 마운트하며 `PYTHONPATH=/workspace/src`를 설정한다. 호스트에서 수정한 제품 코드를 같은 이미지에서 시험할 수 있다.

제품 시험이 생긴 뒤 저장소 루트에서 실행한다.

```powershell
docker compose run --rm --no-deps dev python -m pytest tests/backend tests/gateway -q -p no:cacheprovider
```

현재 위 제품 시험 경로는 구현 전이다. `scripts/dev_docker.ps1 -Mode check`는 하네스·계약 준비 검사이며 제품 수용시험은 **NOT_RUN**이다. 시험용 DB와 결과 파일은 `tmp_path` 등 임시 쓰기 경로를 사용하고 실제 키·계정은 사용하지 않는다.
