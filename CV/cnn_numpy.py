# This is a very rudimentary implementation on a specific acchitecture of convolutional neural networks using NumPy, 
# it assumes zero-padding to be true and the stride to be one, further with the output and the input of
# a convolutional layer have the same spatial size. The maxpooling layer has window size 2x2 and stride 2
# Potential problems: vanishing gradients

# This file only defines the most common layers of the Conv NNs including forward and backward pass throgh these layers

import numpy as np

class Linear():
  '''
  Linear (fully connected) layer: forward pass return output (without activation),
  backward pass return the gradients on parameters and on variable 
  '''

  def __init__(self,weight,bias,input_d):
    self.weight = weight # [in_szie x out_size]
    self.bias = bias # [1 x out_size]
    self.input = input_d # [bathc_size x in_size]

  def forward(self):
    self.output = np.dot(self.input, self.weight) + self.bias # [batch_size x out_size]
    return self.output

  def backward(self,dLdY):
    # dLdY size: [batch_size x out_size]
    dLdx = np.dot(dLdY, np.transpose(self.weight)) # [batch_size x in_size]
    dLdb = (np.sum(dLdY, axis = 0)).reshape(1,-1) # [1 x out_size]
    dLdw = np.dot(np.transpose(self.input), dLdY) # [in_size x out_size]
    return dLdw, dLdb, dLdx



class softmax_with_cross_entropy_loss():
  '''
  This function gives the cross-entropy loss over the batch,
  the label needs to be transposed here since it is a matrix not a vector 
  (in vector cases the shape can be inferred automatically)
  np.diag() here will produce a row vector of lenth [batch_size]
  axis=1 means we are summing along the rows, i.e. the first dimension 
  resulting in a row vector of length [batch_size], then take the log of that vector
  final step is to sum up over the batch_size to get a single number
  The gradient of the logits are also given by dLdz

  '''

  def __init__(self,logit,label):
    self.logit = logit # [batch_szie x 10]
    self.label = label # [batch_szie x 10] (onehot)
    self.loss = np.sum(-np.diag(np.dot(self.logit,np.transpose(self.label))) \
                      + np.log(np.sum(np.exp(self.logit),axis=1))) # scalar

    # The derivative of loss wrt logit ([batch_size x 10]), 
    # returns a gradiant of shape [batch_size x 10]
    self.dLdz = -self.label + np.exp(self.logit) \
    / np.reshape(np.sum(np.exp(self.logit),axis=1),(-1,1))



class ReLU():
  '''
  ReLU non-linearity, shape of the input will not change when ReLU is applied
  '''

  def __init__(self,input_d):
    self.input = input_d

  def forward(self):
    output = np.maximum(self.input, np.zeros(np.shape(self.input))) #[batch_size x in_size]
    return output

  def backward(self,dLdY):
    # dRdx = np.maximum(np.sign(self.input),np.zeros(np.shape(self.input))) # same size as input: [batch_szie x ?]
    dLdR = dLdY * ((self.input > 0) * 1) # [batch_size x in_size]
    return dLdR




class ConV():
  '''
  Convolution layer with zero padding and stride one, weight/bias and filter number
  are given as arguments, no activation function is assumed.
  Forward pass returns output, backward pass return the gradient of loss wrt input
  The gradients of loss wrt weight and bias are defined in Grad_W and Grad_b respectively 
  Here assuming the input has equal spatial size (height = width),
  and the spatial size of the output is the same of the input. In more general cases, the 
  output shape can be obtained by calculating 
  W_out = (W_in - W + P)/S + 1 where W is the width of the weight and P is the number of zeros
  padded along each row (width) of the input, S is the stride
  '''
  
  def __init__(self,input_d,kernel,bias):
    self.input = input_d # [batch_size x H_in x W_in x D_in]
    self.H_in = self.input.shape[1] # H_in
    self.W_in = self.input.shape[2] # W_in
    self.D_in = self.input.shape[3] # D_in
    self.bs = self.input.shape[0] # batch_size
    self.kernel = kernel # i.e. the weight, shape: [H x W x D_in x D]
    self.bias = bias # [1 x D]
    self.kernel_H = self.kernel.shape[0] # H
    self.kernel_W = self.kernel.shape[1] # W
    self.filters = self.kernel.shape[3] # D
    # Size of padded: [batch_size x H_in+2 x W_in+2 x D_in]
    self.padded = np.pad(self.input,((0,0),(1,1),(1,1),(0,0)),'constant') # pad zeros at the boundarys 
    self.padded_size = self.padded.shape[1] # H_in+2 = W_in+2
    
 
  def forward(self):
    # Size of output: [batch_size x H_out x W_out x D] here assuming H_out = H_in = W_out = W_in
    output = np.zeros((self.bs,self.H_in,self.W_in,self.filters))
    # Vertical (Height)

    for i in np.arange(self.padded_size-self.kernel_H + 1): # 14+2-3+1 = 14 so i takes 0-13
      # Horizontal (Widith)
      for j in np.arange(self.padded_size-self.kernel_W + 1):
        for k in np.arange(self.filters):
          # current_scan size: [batch_size x H x W x D_in]
          current_scan = self.padded[:,i:i+self.kernel_H,j:j+self.kernel_W,:]
          # kernel_repeat size : [batch_size x H x W x D_in x D]
          kernel_repeat = np.repeat(np.expand_dims(self.kernel, axis=0),self.bs,axis=0)


          # multiply: [batch_size x H x W x D_in]
          # sum over axis=(1,2,3): [batch_size,]
          # plus bias: [batch_size,]
          output[:,i,j,k] = np.sum(np.multiply(kernel_repeat[:,:,:,:,k],current_scan),axis = (1,2,3)) + self.bias[:,k]
          
    return output

  def backward(self,dLdY):

    padded_dLdY = np.pad(dLdY,((0,0),(1,1),(1,1),(0,0)),'constant')
    self.padded_dLdY_size = padded_dLdY.shape[1] # H_out+2 = W_out+2
    dLdX = np.zeros((self.bs,self.H_in,self.W_in,self.D_in))
    flip_kernel = np.rot90(self.kernel, 2) # flipped for the first two dims (spatial)
    for i in np.arange(self.padded_dLdY_size-self.kernel_H + 1):
      for j in np.arange(self.padded_dLdY_size-self.kernel_W + 1):
        for d in np.arange(self.D_in):
          # current_scan size: [100 x 3 x 3 x D]
          current_scan = padded_dLdY[:,i:i+self.kernel_H,j:j+self.kernel_W,:] # +3 instead of +3-1
          # current_scan_expand = np.expand_dims(current_scan, axis=4) # [100 x 3 x 3 x D x 1]
          flip_kernel_repeat = np.repeat(np.expand_dims(flip_kernel, axis=0),self.bs,axis=0) # [100 x 3 x 3 x D_in x D]
          swap_flip_kernel_repeat = np.swapaxes(flip_kernel_repeat, 3,4) # [100 x 3 x 3 x D x D_in]
          # multiply: [100 x 3 x 3 x D]
          dLdX[:,i,j,d] = np.sum(np.multiply(swap_flip_kernel_repeat[:,:,:,:,d],current_scan),axis=(1,2,3))
    return dLdX

  def Grad_W(self,dLdY):
    # dLdY size: [batch_size x ws x ws x D]
    dLdW = np.zeros((self.kernel_H,self.kernel_W,self.D_in,self.filters))
    window_size = dLdY.shape[1] 
    for d in np.arange(self.D_in):
      for i in np.arange(self.padded_size-window_size+1):  
        for j in np.arange(self.padded_size-window_size+1):
          current_scan = self.padded[:, i:i+window_size, j:j+window_size, d] # [batch_size x ws x ws]
          for k in np.arange(self.filters):
            dLdW[i,j,d,k] = np.sum(np.multiply(dLdY[:,:,:,k],current_scan)) # [bs x ws x ws] .* [bs x ws x ws]
    return dLdW

  def Grad_b(self,dLdY):
    # dLdY: [batch_size x H_out x W_out x D]
    dLdb = np.sum(dLdY, axis = (0,1,2)) # [1 x D]
    return dLdb 

class MaxPool():
  '''Since all the maxpool layers in this model has windows of size [2x2] with stride 2,
     no extra definitions on stride and kernel size are needed.
  '''
  def __init__(self,input_d):
    self.input = input_d # [batch_size x H_in x W_in x D_in]
    self.H_in = self.input.shape[1] # H_in
    self.W_in = self.input.shape[2] # W_in
    self.D_in = self.input.shape[3] # D_in
    self.bs = self.input.shape[0] # batch_size
    # Output shape: [batch_size x H_in/2 x W_in/2 x D_in]
    self.output = np.zeros((self.input.shape[0],self.H_in//2,self.W_in//2,self.D_in))

  def forward(self):
    global_position = np.zeros((self.bs,self.H_in,self.W_in,self.D_in))
    for h in np.arange(self.H_in//2):
      for w in np.arange(self.W_in//2):
        # Take the maximum along axis 1 (height) and 2 (width), here the operand has shape
        # [batch_size x 2 x 2 x D_in]
        self.output[:,h,w,:] = np.amax(self.input[:,2*h:2*h+2,2*w:2*w+2,:],axis=(1,2))
    max_repeat_1 = np.repeat(self.output,2,axis=2)
    max_repeat_2 = np.repeat(max_repeat_1,2,axis=1).reshape(self.bs,self.H_in,self.W_in,self.D_in)
    global_position = (max_repeat_2 == self.input)
    return self.output, global_position

  def backward(self,dLdY,locations):
    '''dLdY is the gradient passed from the previous layer, with spatial size a quarter of the input, (width and height halved)
    '''
    dLdM = np.zeros((self.bs,self.H_in,self.W_in,self.D_in)) # [batch_size x H_in x W_in x D_in]
    dLdY_repeat_1 = np.repeat(dLdY,2,axis=2)
    dLdY_repeat_2 = np.repeat(dLdY_repeat_1,2,axis=1).reshape(self.bs,self.H_in,self.W_in,self.D_in)
    dLdM = locations * dLdY_repeat_2
    return dLdM










