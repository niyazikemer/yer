import torch.nn as nn
import torch
import numpy as np
import torchvision.transforms as transforms
import torch.nn as nn
import torch.nn.functional as F

# define the CNN architecture
class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()

        self.fc1 = nn.Linear(20 * 20 * 3, 500)
        self.fc2 = nn.Linear(500, 100)
        self.fc3 = nn.Linear(100, 3)


    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = F.tanh(self.fc3(x))
        # x = F.softmax(x, dim=1)
        return x

# create a complete CNN
model = Net()


# model.load_state_dict(torch.load('vanilla_models/model_cifar.pt'))

train_on_gpu = torch.cuda.is_available()

# move tensors to GPU if CUDA is available
# if train_on_gpu:
#     model.cuda()
# # model.eval()

def model_loader():
    model_list=[]
    use_cuda = torch.cuda.is_available()
    
    for i in range(20):
        model_list.append(Net())
        model_list[i].load_state_dict(torch.load(f'vanilla_models/{i%5}.pt'))
    # print(model_list)    
    for model in model_list:
        for param in model.parameters():
            param.requires_grad = False
        model.eval()
        if use_cuda:
            model = model.cuda()
            
    return model_list


def predict(np_im,model):
    '''
    Use pre-trained VGG-16 model to obtain index corresponding to 
    predicted ImageNet class for image at specified path
    
    Args:
        img_path: path to an image
        
    Returns:
        Index corresponding to VGG-16 model's prediction
    '''
    
    ## TODO: Complete the function.
    ## Load and pre-process an image from the given img_path
    ## Return the *index* of the predicted class for that image
    
    # do I need to use these two?
    # if use_cuda:
    #     model.cuda()    
    # model.eval()    
    
    with torch.no_grad():
       
        image = process_image(np_im)
        if use_cuda:
            image = image.type(torch.FloatTensor).cuda()   
        #I do not understand why we shold do this why not 3 dimensions are not sufficent.
        #print(image.shape)
        image = image.unsqueeze(0)
        #print(image.shape)
        
        output = model.forward(image)
        output =output.cpu().detach().numpy()
        # print(output)
    return output


    
def process_image(np_im):
    ''' Scales, crops, and normalizes a PIL image for a PyTorch model,
        returns an Numpy array
    '''
    np_im=np_im.reshape(1,1200)
    transformations = transforms.Compose([transforms.ToTensor()])
    torch_image = transformations(np_im).float()    
    return torch_image

use_cuda = torch.cuda.is_available()
torch.save(model.state_dict(),f'vanilla_models/000.pt')
print(model)