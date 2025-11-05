import pandas as pd

from particle_analysis.volume.optimizer import select_radius_by_constraints


def df_from(rows):
    return pd.DataFrame(rows, columns=[
        'radius', 'particle_count', 'largest_particle_ratio', 'mean_contacts'
    ])


def test_select_both_conditions_met():
    # r*=3 where largest_ratio <= 0.05
    df = df_from([
        [1,  50, 0.50, 1.0],
        [2, 200, 0.20, 3.0],
        [3, 400, 0.04, 5.0],  # r* here
        [4, 405, 0.03, 6.0],  # Δcount=5 (<= 0.3% of 400 -> 1.2 -> ceil=2) -> not pass
        [5, 402, 0.03, 6.5],  # Δcount=-3 (<= 2) & contacts in [4,10] -> pass
    ])

    sel = select_radius_by_constraints(df, tau_ratio=0.05, tau_gain_rel=0.003, contacts_range=(4, 10))
    assert sel['selected_radius'] == 5
    assert sel['reason'] == 'both'


def test_select_contacts_only_fallback():
    # r*=2, but Δcount always big; contacts satisfied at r=3 first
    df = df_from([
        [1, 100, 0.10, 2.0],
        [2, 300, 0.05, 3.5],  # r*
        [3, 500, 0.04, 7.0],  # contacts in range
        [4, 900, 0.03, 7.5],
    ])
    sel = select_radius_by_constraints(df, tau_ratio=0.05, tau_gain_rel=0.003, contacts_range=(4, 10))
    assert sel['selected_radius'] == 3
    assert sel['reason'] == 'contacts_only'


def test_select_r_star_fallback():
    # r*=2, contacts never in range
    df = df_from([
        [1, 100, 0.10, 2.0],
        [2, 300, 0.05, 3.0],  # r*
        [3, 310, 0.04, 3.5],
        [4, 315, 0.03, 3.8],
    ])
    sel = select_radius_by_constraints(df, tau_ratio=0.05, tau_gain_rel=0.003, contacts_range=(4, 10))
    assert sel['selected_radius'] == 2
    assert sel['reason'] == 'r_star'


def test_select_max_r_when_no_r_star():
    # largest_particle_ratio never <= 0.05, no contacts in range -> pick max r
    df = df_from([
        [1, 100, 0.80, 2.0],
        [2, 200, 0.70, 3.0],
        [3, 300, 0.60, 3.5],
    ])
    sel = select_radius_by_constraints(df, tau_ratio=0.05, tau_gain_rel=0.003, contacts_range=(6, 7))
    assert sel['selected_radius'] == 3
    assert sel['reason'] == 'max_r'


