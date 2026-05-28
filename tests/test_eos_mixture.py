import numpy as np
import math
from epdm_sim.eos import mixture_parameters, mixture_ln_phi, cubic_eos_mixture_k_values

def test_mixture_parameters_binary_interaction():
    # Test mixture a, b with kij
    z = {"ethylene": 0.5, "propylene": 0.5}
    T = 373.15
    a, b = mixture_parameters(z, T, "PR")
    assert a > 0
    assert b > 0
    
    # Verify that kij impact is captured (though simplified in our model)
    # If we change composition, a and b should change
    z2 = {"ethylene": 0.2, "propylene": 0.8}
    a2, b2 = mixture_parameters(z2, T, "PR")
    assert a != a2
    assert b != b2

def test_mixture_ln_phi_bounds():
    z = {"ethylene": 0.8, "hexane": 0.2}
    T = 350.0
    P = 1.0e6
    phi_v = mixture_ln_phi(z, T, P, "PR", "vapor")
    phi_l = mixture_ln_phi(z, T, P, "PR", "liquid")
    
    for comp in z:
        assert comp in phi_v
        assert comp in phi_l
        # Fugacity coefficients should be physical
        assert -10.0 < phi_v[comp] < 2.0
        assert -20.0 < phi_l[comp] < 2.0

def test_mixture_k_values_consistency():
    z = {"ethylene": 0.1, "propylene": 0.1, "hexane": 0.8}
    T = 300.0 
    P = 1.0e5 # 0.1 MPa
    k_vals = cubic_eos_mixture_k_values(z, T, P, "PR")
    print(f"DEBUG K-VALUES at {T}K, {P}Pa: {k_vals}")
    
    # Ethylene should be more volatile than hexane
    assert k_vals["ethylene"] > k_vals["hexane"]
    # Propylene should be in between
    assert k_vals["ethylene"] > k_vals["propylene"] > k_vals["hexane"]
