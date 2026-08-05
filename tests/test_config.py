"""Testes de kata.config — os comandos de verificação do projeto alvo.

Config quebrada tem de ser erro nomeado, nunca default silencioso: cair no
ruff calado faria o kata reportar sucesso de uma verificação que o projeto
nunca pediu.
"""

from __future__ import annotations

import json

import pytest

from kata.config import (
    DEFAULT_COVERAGE_PATTERN,
    DEFAULT_GATE,
    ConfigError,
    VerifyConfig,
    config_path,
    load_verify_config,
)


def _escreve(tmp_path, conteudo: str, nome: str = "config.yaml"):
    kata = tmp_path / ".kata"
    kata.mkdir(exist_ok=True)
    (kata / nome).write_text(conteudo, encoding="utf-8")
    return tmp_path


class TestDefaults:
    """Sem arquivo, o comportamento anterior é reproduzido intacto."""

    def test_sem_arquivo_devolve_defaults(self, tmp_path) -> None:
        cfg = load_verify_config(cwd=tmp_path)
        assert cfg == VerifyConfig()
        assert cfg.lint is None and cfg.test is None and cfg.coverage is None
        assert cfg.gate is None
        assert cfg.coverage_pattern == DEFAULT_COVERAGE_PATTERN
        assert cfg.customizado is False

    def test_sem_arquivo_nao_ha_caminho(self, tmp_path) -> None:
        assert config_path(cwd=tmp_path) is None

    def test_arquivo_vazio_devolve_defaults(self, tmp_path) -> None:
        _escreve(tmp_path, "")
        assert load_verify_config(cwd=tmp_path) == VerifyConfig()

    def test_sem_secao_verify_devolve_defaults(self, tmp_path) -> None:
        _escreve(tmp_path, "outra_coisa: 1\n")
        assert load_verify_config(cwd=tmp_path) == VerifyConfig()

    def test_gate_default_e_setenta(self) -> None:
        assert DEFAULT_GATE == 70.0


class TestComandos:
    """Cada papel aceita string ou lista, e um papel omitido cai no default."""

    def test_string_e_dividida_como_o_shell(self, tmp_path) -> None:
        _escreve(tmp_path, "verify:\n  lint: npx eslint src tests\n")
        cfg = load_verify_config(cwd=tmp_path)
        assert cfg.lint == ["npx", "eslint", "src", "tests"]
        assert cfg.customizado is True

    def test_string_respeita_aspas(self, tmp_path) -> None:
        _escreve(tmp_path, "verify:\n  test: npm test -- --reporter 'dot compact'\n")
        cfg = load_verify_config(cwd=tmp_path)
        assert cfg.test == ["npm", "test", "--", "--reporter", "dot compact"]

    def test_lista_e_usada_como_veio(self, tmp_path) -> None:
        _escreve(tmp_path, 'verify:\n  test: ["go", "test", "./..."]\n')
        assert load_verify_config(cwd=tmp_path).test == ["go", "test", "./..."]

    def test_papel_omitido_continua_none(self, tmp_path) -> None:
        _escreve(tmp_path, "verify:\n  lint: go vet ./...\n")
        cfg = load_verify_config(cwd=tmp_path)
        assert cfg.lint == ["go", "vet", "./..."]
        assert cfg.test is None
        assert cfg.coverage is None

    def test_coverage_pattern_e_gate(self, tmp_path) -> None:
        _escreve(
            tmp_path,
            "verify:\n"
            "  coverage: npx vitest run --coverage\n"
            "  coverage_pattern: 'All files\\s+\\|\\s+([\\d.]+)'\n"
            "  gate: 85\n",
        )
        cfg = load_verify_config(cwd=tmp_path)
        assert cfg.coverage == ["npx", "vitest", "run", "--coverage"]
        assert cfg.coverage_pattern == r"All files\s+\|\s+([\d.]+)"
        assert cfg.gate == 85.0

    def test_json_e_aceito(self, tmp_path) -> None:
        _escreve(
            tmp_path,
            json.dumps({"verify": {"lint": ["cargo", "clippy"]}}),
            nome="config.json",
        )
        assert load_verify_config(cwd=tmp_path).lint == ["cargo", "clippy"]

    def test_yml_tambem_e_encontrado(self, tmp_path) -> None:
        _escreve(tmp_path, "verify:\n  lint: shellcheck src\n", nome="config.yml")
        assert load_verify_config(cwd=tmp_path).lint == ["shellcheck", "src"]

    def test_config_path_aponta_o_arquivo(self, tmp_path) -> None:
        _escreve(tmp_path, "verify: {}\n")
        caminho = config_path(cwd=tmp_path)
        assert caminho is not None and caminho.name == "config.yaml"


class TestErros:
    """Config presente porém inválida aborta com mensagem, e não vira default."""

    def test_comando_vazio_em_string(self, tmp_path) -> None:
        _escreve(tmp_path, "verify:\n  lint: ''\n")
        with pytest.raises(ConfigError, match="lint: comando vazio"):
            load_verify_config(cwd=tmp_path)

    def test_comando_vazio_em_lista(self, tmp_path) -> None:
        _escreve(tmp_path, "verify:\n  test: []\n")
        with pytest.raises(ConfigError, match="test: comando vazio"):
            load_verify_config(cwd=tmp_path)

    def test_lista_com_nao_string(self, tmp_path) -> None:
        _escreve(tmp_path, "verify:\n  test: [pytest, 3]\n")
        with pytest.raises(ConfigError, match="só strings"):
            load_verify_config(cwd=tmp_path)

    def test_tipo_errado_no_comando(self, tmp_path) -> None:
        _escreve(tmp_path, "verify:\n  lint: {cmd: x}\n")
        with pytest.raises(ConfigError, match="esperava string ou lista"):
            load_verify_config(cwd=tmp_path)

    def test_topo_nao_e_mapa(self, tmp_path) -> None:
        _escreve(tmp_path, "- um\n- dois\n")
        with pytest.raises(ConfigError, match="esperava um mapa no topo"):
            load_verify_config(cwd=tmp_path)

    def test_verify_nao_e_mapa(self, tmp_path) -> None:
        _escreve(tmp_path, "verify: [1, 2]\n")
        with pytest.raises(ConfigError, match="`verify` deve ser um mapa"):
            load_verify_config(cwd=tmp_path)

    @pytest.mark.parametrize("valor", ["false", "[]", "''"])
    def test_verify_tipo_vazio_nao_cai_em_default(self, tmp_path, valor) -> None:
        _escreve(tmp_path, f"verify: {valor}\n")
        with pytest.raises(ConfigError, match="`verify` deve ser um mapa"):
            load_verify_config(cwd=tmp_path)

    def test_gate_nao_numerico(self, tmp_path) -> None:
        _escreve(tmp_path, "verify:\n  gate: muito\n")
        with pytest.raises(ConfigError, match="`verify.gate` deve ser número"):
            load_verify_config(cwd=tmp_path)

    @pytest.mark.parametrize("gate", [-1, 101, "NaN"])
    def test_gate_fora_do_intervalo_reprova(self, tmp_path, gate) -> None:
        _escreve(tmp_path, f"verify:\n  gate: {gate}\n")
        with pytest.raises(ConfigError, match="deve ser número|entre 0 e 100"):
            load_verify_config(cwd=tmp_path)

    def test_pattern_nao_string(self, tmp_path) -> None:
        _escreve(tmp_path, "verify:\n  coverage_pattern: 42\n")
        with pytest.raises(ConfigError, match="coverage_pattern` deve ser string"):
            load_verify_config(cwd=tmp_path)

    def test_pattern_invalido_reprova_no_carregamento(self, tmp_path) -> None:
        _escreve(tmp_path, "verify:\n  coverage_pattern: '['\n")
        with pytest.raises(ConfigError, match="coverage_pattern.*inválido"):
            load_verify_config(cwd=tmp_path)

    def test_yaml_ilegivel(self, tmp_path) -> None:
        _escreve(tmp_path, "verify:\n  lint: [nao\n    fecha\n")
        with pytest.raises(ConfigError, match="não foi possível ler"):
            load_verify_config(cwd=tmp_path)

    def test_json_ilegivel(self, tmp_path) -> None:
        _escreve(tmp_path, "{nao é json}", nome="config.json")
        with pytest.raises(ConfigError, match="não foi possível ler"):
            load_verify_config(cwd=tmp_path)


class TestSemPyYAML:
    """Sem PyYAML o kata cai em JSON, como já faz para os arquivos de tarefa."""

    def test_yaml_lido_como_json_quando_falta_pyyaml(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr("kata.config._HAS_YAML", False)
        _escreve(tmp_path, json.dumps({"verify": {"lint": "go vet ./..."}}))
        assert load_verify_config(cwd=tmp_path).lint == ["go", "vet", "./..."]
