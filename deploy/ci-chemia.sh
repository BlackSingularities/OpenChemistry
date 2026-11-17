# Kopia pliku /opt/apps/bin/ci.d/chemia.sh z serwera (instalowany ręcznie przez administratora – CI go nie zmienia).
# OpenChemistry (redzikowski.com/chemia): archiwum repozytorium na stdin, obraz budowany na serwerze.
APP_DIR=/opt/apps/chemia
ALLOW=("$APP_DIR")
COMPOSE_ARGS=(-f compose.yml -p chemia)
ci_deploy() {
  local i
  receive_tar "$WORK/src" 60
  cd "$WORK/src"
  ALLOW=("$WORK/src" "$APP_DIR")
  compose_check
  ALLOW=("$APP_DIR")
  rm -rf "$APP_DIR.new" "$APP_DIR.old"
  cp -a "$WORK/src" "$APP_DIR.new"
  [[ -d $APP_DIR ]] && mv "$APP_DIR" "$APP_DIR.old"
  mv "$APP_DIR.new" "$APP_DIR"
  cd "$APP_DIR"
  if ! compose up -d --build --remove-orphans; then
    echo "Budowanie nie powiodło się – przywracam poprzednią wersję"
    if [[ -d $APP_DIR.old ]]; then rm -rf "$APP_DIR"; mv "$APP_DIR.old" "$APP_DIR"; cd "$APP_DIR"; compose up -d --build; fi
    exit 1
  fi
  for i in $(seq 1 20); do
    docker exec chemia python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)" && break
    [[ $i == 20 ]] && { echo "Kontener nie odpowiada na /api/health"; exit 1; }
    sleep 3
  done
  proxy_conf deploy/nginx.conf /opt/apps/proxy/conf.d/apps/chemia.conf
  reload_proxy
  health https://redzikowski.com/chemia/api/health
  rm -rf "$APP_DIR.old"
}
