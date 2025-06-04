import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# Test cases for checkSyntax
def test_check_syntax_valid(client):
    valid_program = """
    int main(void) {
        return 0;
    }
    """
    response = client.post("/checkSyntax", json={"program": valid_program})
    assert response.status_code == 200
    data = response.get_json()
    assert data["isSyntaxCorrect"] is True

def test_check_syntax_invalid(client):
    invalid_program = """
    void main(void) {
        int x;
        x = 5
        output(x);
    }
    """ 
    response = client.post("/checkSyntax", json={"program": invalid_program})
    assert response.status_code == 200
    data = response.get_json()
    assert data["isSyntaxCorrect"] is False
    assert isinstance(data["line"], int)

def test_check_syntax_empty_input(client):
    response = client.post("/checkSyntax", json={"program": ""})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data

def test_check_syntax_missing_program_field(client):
    response = client.post("/checkSyntax", json={})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    

# Test cases for run Compile
def test_run_compile_valid(client):
    valid_program = """
    void main(void) {
        int x;
        x = 5;
        output(x);
    }
    """
    response = client.post("/runCompile", json={"program": valid_program})
    print(response.data)
    assert response.status_code == 200
    data = response.get_json()
    assert "outputs" in data
    assert data["outputs"] == ["5"]
    
def test_run_compile_invalid(client):
    invalid_program = """
    void main(void) {
        int x;
        x = 5;
        output(x)
    }
    """
    response = client.post("/runCompile", json={"program": invalid_program})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data

def test_run_compile_empty_input(client):
    response = client.post("/runCompile", json={"program": ""})
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
    
def test_run_compile_timeout(client):
    # This test assumes that the program will run indefinitely
    infinite_loop_program = """
    void main(void) {
        int x;
        x = 0;
        while (x < 5) {
            output(x);
        }
    }
    """
    response = client.post("/runCompile", json={"program": infinite_loop_program})
    assert response.status_code == 408
    data = response.get_json()
    assert "error" in data
    assert data["error"] == "Timeout expired while running the compiled file"