import math
def Bz(z, D=6.0, L=3.0, Br=1.19):
    """axial field (mT) of a disc magnet at distance z (mm) from its face"""
    R=D/2
    return Br/2*((L+z)/math.sqrt(R*R+(L+z)**2) - z/math.sqrt(R*R+z*z))*1000
if __name__=="__main__":
    for D,L,Br,nm in [(6,3,1.19,"6x3 N35"),(6,3,1.45,"6x3 N52"),(5,2,1.19,"5x2 N35"),(8,3,1.19,"8x3 N35"),(6,2,1.19,"6x2 N35")]:
        print(nm, " ".join(f"{z}:{Bz(z,D,L,Br):.0f}" for z in [1,1.5,2,2.5,3,3.5,4,5,6,7,8,9,10,12]))
