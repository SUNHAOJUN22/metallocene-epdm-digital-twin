from epdm_sim.posterior import posterior_to_uncertainty_inputs, run_lightweight_mcmc


def test_posterior_sampling_finite_reproducible():
    a = run_lightweight_mcmc(n_steps=30, seed=42)
    b = run_lightweight_mcmc(n_steps=30, seed=42)
    assert not a.samples.empty
    assert 0.0 <= a.acceptance_rate <= 1.0
    assert a.samples.equals(b.samples)
    uncertainty = posterior_to_uncertainty_inputs(a)
    assert uncertainty
    assert all(value >= 0 for value in uncertainty.values())

