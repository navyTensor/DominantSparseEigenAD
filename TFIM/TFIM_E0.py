"""
    Several different approaches of computing various order of derivatives of the 
ground state energy per site of 1D TFIM.
"""

"""
    These statements are needed only when the package is not permanently installed
in user's system.
"""
import sys
sys.path.append("../")

import numpy as np
import torch
from TFIM import TFIM

def E0_analytic(model):
    """
        Computing the ground state energy itself using analytic result based on
    Jordan-Wigner transformation. The various order derivatives of it are then
    computed by AD.
    """
    ks = torch.linspace(-(model.N-1)/2, (model.N-1)/2, steps=model.N, dtype=torch.float64) \
                / model.N * 2 * np.pi
    epsilon_ks = 2 * torch.sqrt(model.g**2 - 2 * model.g * torch.cos(ks) + 1)
    E0 = - 0.5 * epsilon_ks.sum()
    dE0, = torch.autograd.grad(E0, model.g, create_graph=True)
    d2E0, = torch.autograd.grad(dE0, model.g)
    return E0.item() / model.N, \
           dE0.item() / model.N, \
           d2E0.item() / model.N

def E0_torchAD(model):
    """
        Compute various order of derivatives of the ground state energy using AD
    of the full eigensolver built in Pytorch.
    """
    Es, psis = torch.symeig(model.Hmatrix, eigenvectors=True)
    E0 = Es[0]
    dE0, = torch.autograd.grad(E0, model.g, create_graph=True)
    d2E0, = torch.autograd.grad(dE0, model.g, retain_graph=True)
    return E0.item() / model.N, \
           dE0.item() / model.N, \
           d2E0.item() / model.N

def E0_matrixAD(model, k):
    """
        Compute various order of derivatives of the ground state energy using the
    DominantSymeig primitive, where the matrix to be diagonalized is represented as
    the normal form of a torch.Tensor.
    """
    from DominantSparseEigenAD.Lanczos import DominantSymeig
    dominant_symeig = DominantSymeig.apply
    E0, psi0 = dominant_symeig(model.Hmatrix, k)
    dE0, = torch.autograd.grad(E0, model.g, create_graph=True)
    d2E0, = torch.autograd.grad(dE0, model.g)
    return E0.item() / model.N, \
           dE0.item() / model.N, \
           d2E0.item() / model.N

def E0_sparseAD(model, k):
    """
        Compute various order of derivatives of the ground state energy using the
    DominantSparseSymeig primitive, where the matrix to be diagonalized is "sparse"
    and represented as a function.
    """
    import DominantSparseEigenAD.Lanczos as lanczos
    lanczos.setDominantSparseSymeig(model.H, model.Hadjoint_to_gadjoint)
    dominant_sparse_symeig = lanczos.DominantSparseSymeig.apply
    E0, psi0 = dominant_sparse_symeig(model.g, k, model.dim)
    dE0, = torch.autograd.grad(E0, model.g, create_graph=True)
    d2E0, = torch.autograd.grad(dE0, model.g)
    return E0.item() / model.N, \
           dE0.item() / model.N, \
           d2E0.item() / model.N

def E0_manual_sparseAD(model, k):
    """
        The task of using AD to compute the derivatives up to 2nd order of the
    ground state energy is so trivial that we can implemented it "by hand"
    instead of making use of any Function primitives.
    """
    from DominantSparseEigenAD.Lanczos import symeigLanczos
    from DominantSparseEigenAD.CG import CG_torch
    E0, psi0 = symeigLanczos(model.H, k, extreme="min", sparse=True, dim=model.dim)
    dE0 = model.pHpg(psi0).matmul(psi0) 

    A = lambda v: model.H(v) - E0 * v
    b = 2 * model.pHpg(psi0)
    b = b - torch.matmul(psi0, b) * psi0
    initialx = torch.randn(model.dim, dtype=b.dtype)
    initialx = initialx - torch.matmul(psi0, initialx) * psi0
    lambda0 = CG_torch(A, b, initialx, sparse=True)
    d2E0 = - model.pHpg(psi0).matmul(lambda0) 

    return E0.item() / model.N, \
           dE0.item() / model.N, \
           d2E0.item() / model.N

if __name__ == "__main__":
    N = 10
    model = TFIM(N)
    k = 300
    Npoints = 100
    gs = np.linspace(0.45, 1.6, num=Npoints)
    E0s_analytic = np.empty(Npoints)
    E0s_torchAD = np.empty(Npoints)
    E0s_matrixAD = np.empty(Npoints)
    E0s_sparseAD = np.empty(Npoints)
    E0s_manual_sparseAD = np.empty(Npoints)

    dE0s_analytic = np.empty(Npoints)
    dE0s_torchAD = np.empty(Npoints)
    dE0s_matrixAD = np.empty(Npoints)
    dE0s_sparseAD = np.empty(Npoints)
    dE0s_manual_sparseAD = np.empty(Npoints)

    d2E0s_analytic = np.empty(Npoints)
    d2E0s_torchAD = np.empty(Npoints)
    d2E0s_matrixAD = np.empty(Npoints)
    d2E0s_sparseAD = np.empty(Npoints)
    d2E0s_manual_sparseAD = np.empty(Npoints)

    print("g    E0_analytic    E0_torchAD    E0_matrixAD    E0_sparseAD    E0_manual_sparseAD    "\
          "dE0_analytic    dE0_torchAD    dE0_matrixAD    dE0_sparseAD    dE0_manual_sparseAD    "\
          "d2E0_analytic    d2E0_torchAD    d2E0_matrixAD    d2E0_sparseAD    d2E0_manual_sparseAD")
    for i in range(Npoints):
        model.g = torch.Tensor([gs[i]]).to(torch.float64)
        model.g.requires_grad_(True)

        E0s_analytic[i], dE0s_analytic[i], d2E0s_analytic[i] = E0_analytic(model)

        model.setHmatrix()
        E0s_torchAD[i], dE0s_torchAD[i], d2E0s_torchAD[i] = E0_torchAD(model)
        E0s_matrixAD[i], dE0s_matrixAD[i], d2E0s_matrixAD[i] = E0_matrixAD(model, k)

        E0s_sparseAD[i], dE0s_sparseAD[i], d2E0s_sparseAD[i] = E0_sparseAD(model, k)

        E0s_manual_sparseAD[i], dE0s_manual_sparseAD[i], d2E0s_manual_sparseAD[i] \
                = E0_manual_sparseAD(model, k)


        print(gs[i], E0s_analytic[i], E0s_torchAD[i], E0s_matrixAD[i], E0s_sparseAD[i], E0s_manual_sparseAD[i],
              dE0s_analytic[i], dE0s_torchAD[i], dE0s_matrixAD[i], dE0s_sparseAD[i], dE0s_manual_sparseAD[i],
              d2E0s_analytic[i], d2E0s_torchAD[i], d2E0s_matrixAD[i], d2E0s_sparseAD[i], d2E0s_manual_sparseAD[i])

    import matplotlib.pyplot as plt
    plt.plot(gs, E0s_analytic, label="Analytic result")
    plt.plot(gs, E0s_torchAD, label="AD: torch")
    plt.plot(gs, E0s_matrixAD, label="AD: normal representation")
    plt.plot(gs, E0s_sparseAD, label="AD: sparse representation")
    plt.plot(gs, E0s_manual_sparseAD, label="AD: sparse representation(manually)")
    plt.legend()
    plt.xlabel("$g$")
    plt.ylabel("$\\frac{E_0}{N}$")
    plt.title("Ground state energy per site of 1D TFIM\n" \
            "$H = - \\sum_{i=0}^{N-1} (g\\sigma_i^x + \\sigma_i^z \\sigma_{i+1}^z)$\n" \
            "$N=%d$" % model.N)
    plt.show()
    plt.plot(gs, dE0s_analytic, label="Analytic result")
    plt.plot(gs, dE0s_torchAD, label="AD: torch")
    plt.plot(gs, dE0s_matrixAD, label="AD: normal representation")
    plt.plot(gs, dE0s_sparseAD, label="AD: sparse representation")
    plt.plot(gs, dE0s_manual_sparseAD, label="AD: sparse representation(manually)")
    plt.legend()
    plt.xlabel("$g$")
    plt.ylabel("$\\frac{1}{N} \\frac{\\partial E_0}{\\partial g}$")
    plt.title("1st derivative w.r.t. $g$ of ground state energy per site of 1D TFIM\n" \
            "$H = - \\sum_{i=0}^{N-1} (g\\sigma_i^x + \\sigma_i^z \\sigma_{i+1}^z)$\n" \
            "$N=%d$" % model.N)
    plt.show()
    plt.plot(gs, d2E0s_analytic, label="Analytic result")
    plt.plot(gs, d2E0s_torchAD, label="AD: torch")
    plt.plot(gs, d2E0s_matrixAD, label="AD: normal representation")
    plt.plot(gs, d2E0s_sparseAD, label="AD: sparse representation")
    plt.plot(gs, d2E0s_manual_sparseAD, label="AD: sparse representation(manually)")
    plt.legend()
    plt.xlabel("$g$")
    plt.ylabel("$\\frac{1}{N} \\frac{\\partial^2 E_0}{\\partial g^2}$")
    plt.title("2nd derivative w.r.t. $g$ of ground state energy per site of 1D TFIM\n" \
            "$H = - \\sum_{i=0}^{N-1} (g\\sigma_i^x + \\sigma_i^z \\sigma_{i+1}^z)$\n" \
            "$N=%d$" % model.N)
    plt.show()